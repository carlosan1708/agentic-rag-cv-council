"""Module for rendering the analysis results step in the application."""

import streamlit as st

from logger import logger
from models import Persona
from services.analysis_service import (
    ROLE_BOARD_HEAD,
    ROLE_COVER_LETTER,
    ROLE_OPTIMIZER,
    ROLE_REFORMATTER,
    AnalysisService,
)
from services.ats_service import ATSService
from services.cv_service import CVService
from services.history_service import HistoryService
from state_manager import state_manager


def _collect_selected_personas():
    """Combines pre-defined and custom personas selected by the user."""
    selected_personas = list(st.session_state.get("board_agents", []))
    for custom in state_manager.custom_agents:
        selected_personas.append(
            Persona(
                name=custom["name"],
                role=custom.get("role", custom["name"]),
                goal=custom.get("goal", f"Provide specialized analysis as {custom['name']}"),
                backstory=custom.get("backstory", custom.get("prompt", "")),
            )
        )
    return selected_personas


def _run_analysis():
    """Execute the CrewAI analysis process."""
    try:
        selected_personas = _collect_selected_personas()

        st.write("### 📊 Live Analysis Board")
        tabs = st.tabs(["📋 Board Report", "🛠️ Minimal Changes", "📄 Final CV"])

        with tabs[0]:
            board_placeholder = st.empty()
            board_placeholder.info("⏳ Waiting for Board Head synthesis...")
        with tabs[1]:
            changes_placeholder = st.empty()
            changes_placeholder.info("⏳ Waiting for optimization suggestions...")
        with tabs[2]:
            final_cv_placeholder = st.empty()
            final_cv_placeholder.info("⏳ Waiting for final CV reformatting...")

        def on_task_complete(output):
            """Callback for updating UI when a task completes."""
            try:
                role = output.agent
                if hasattr(role, "role"):
                    role = role.role
                role = str(role)

                clean_text = CVService.clean_markdown_code_blocks(str(output.raw))

                if ROLE_BOARD_HEAD in role or "Board Head" in role:
                    board_placeholder.markdown(clean_text)
                    st.toast("✅ Board Report Ready!", icon="📋")
                elif "Optimizer" in role:
                    changes_placeholder.markdown(clean_text)
                    st.toast("✅ Minimal Changes Ready!", icon="🛠️")
                elif "Reformatter" in role:
                    final_cv_placeholder.markdown(clean_text)
                    st.toast("✅ Final CV Ready!", icon="📄")
                elif "Cover Letter" in role:
                    st.toast("✅ Cover Letter Ready!", icon="✉️")
            except Exception as e:
                logger.error(f"Error in task callback: {e}")

        with st.status("🚀 The Board is now in session...", expanded=True) as status:
            st.write("🔍 Assembling the team of specialists...")
            crew = AnalysisService.create_analysis_crew(
                selected_personas=selected_personas,
                cv_content=st.session_state.cv_content,
                job_description=state_manager.job.description,
                config=state_manager.config,
                task_callback=on_task_complete,
                include_cover_letter=st.session_state.get("generate_cover_letter", False),
                debate_mode=st.session_state.get("debate_mode", False),
            )

            st.write("🤖 Specialists are analyzing your CV against the job description...")
            result = AnalysisService.kickoff_with_retry(crew)

            st.write("📝 Analysis complete!")
            status.update(label="✅ Analysis Complete!", state="complete", expanded=False)

            state_manager.crew_result = result
            st.session_state.token_usage = AnalysisService.get_token_usage(result)
            st.session_state.history_saved = False
            st.rerun()
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        st.error(f"Analysis failed: {str(e)}")


def _extract_outputs(result):
    """Extracts the individual reports from the crew result, keyed by agent role."""

    def clean(text, fallback):
        return CVService.clean_markdown_code_blocks(str(text)) if text else fallback

    board_report = clean(AnalysisService.get_output_by_role(result, ROLE_BOARD_HEAD), str(result))
    minimal_changes = clean(AnalysisService.get_output_by_role(result, ROLE_OPTIMIZER), "Optimization data not found.")
    final_cv = clean(AnalysisService.get_output_by_role(result, ROLE_REFORMATTER), str(result))
    cover_letter = AnalysisService.get_output_by_role(result, ROLE_COVER_LETTER)
    cover_letter = CVService.clean_markdown_code_blocks(str(cover_letter)) if cover_letter else None
    return board_report, minimal_changes, final_cv, cover_letter


def _render_ats_tab(final_cv: str):
    """Renders the deterministic ATS score dashboard."""
    job_description = state_manager.job.description
    original_cv = st.session_state.cv_content
    if not job_description:
        st.info("No job description available for scoring.")
        return

    reports = ATSService.compare(original_cv, final_cv, job_description)
    before, after = reports["before"], reports["after"]

    st.markdown("#### ATS Match Score")
    st.caption("Deterministic keyword & structure analysis - no AI involved, fully reproducible.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Original CV", f"{before.score}/100")
    col2.metric("Optimized CV", f"{after.score}/100", delta=after.score - before.score)
    col3.metric("Keyword Coverage", f"{round(after.keyword_coverage * 100)}%")
    st.progress(after.score / 100)

    if after.missing_keywords:
        st.markdown("**Keywords from the job description still missing in the optimized CV:**")
        st.write(", ".join(f"`{k}`" for k in after.missing_keywords[:20]))
    else:
        st.success("The optimized CV covers all detected keywords from the job description.")

    st.markdown("**Section checklist (optimized CV):**")
    for name, present in after.section_checks.items():
        st.markdown(f"{'✅' if present else '❌'} {name}")

    for warning in after.warnings:
        st.warning(warning)


def _render_interview_prep_tab(board_report: str):
    """Renders the on-demand interview preparation guide."""
    st.info("Generate likely interview questions and STAR model answers based on the board's findings.")
    if st.session_state.get("interview_prep"):
        st.markdown(st.session_state.interview_prep)
        if st.button("🔄 Regenerate Interview Prep"):
            st.session_state.interview_prep = ""
            st.rerun()
        return

    if st.button("🎤 Generate Interview Prep", type="primary", use_container_width=True):
        with st.spinner("The board is preparing your interview guide..."):
            try:
                prep = AnalysisService.generate_interview_prep(
                    cv_content=st.session_state.cv_content,
                    job_description=state_manager.job.description,
                    board_report=board_report,
                    config=state_manager.config,
                )
                st.session_state.interview_prep = CVService.clean_markdown_code_blocks(prep)
                st.rerun()
            except Exception as e:
                logger.error(f"Interview prep generation failed: {e}")
                st.error(f"Could not generate interview prep: {e}")


def _save_to_history(board_report, minimal_changes, final_cv, cover_letter):
    """Persists the completed analysis locally, once per run."""
    if st.session_state.get("history_saved"):
        return
    try:
        ats_score = None
        if state_manager.job.description:
            ats_score = ATSService.score_cv(final_cv, state_manager.job.description).score
        HistoryService.save_analysis(
            job_description=state_manager.job.description,
            board_report=board_report,
            minimal_changes=minimal_changes,
            final_cv=final_cv,
            cover_letter=cover_letter or "",
            ats_score=ats_score,
            owner=st.session_state.history_owner,
        )
        st.session_state.history_saved = True
    except Exception as e:
        logger.error(f"Failed to save history: {e}")


def render_results_step():
    """Render the analysis results step UI."""
    st.subheader("Step 5: Board Recommendations")

    if not state_manager.crew_result:
        predefined = state_manager.selected_persona_names
        custom = [a["name"] for a in state_manager.custom_agents]
        all_specialists = predefined + custom

        st.markdown("### Analysis Summary\nThe following specialists will analyze your CV:")

        if all_specialists:
            st.markdown("- " + "\n- ".join(all_specialists))
        else:
            st.warning("No specialists selected. Please go back and choose at least one.")

        st.checkbox(
            "✉️ Also generate a tailored cover letter & outreach messages",
            key="generate_cover_letter",
        )

        st.info("Click the button below to start the analysis.")
        st.warning("⏳ **Note:** The process could take up to **2 minutes**.")

        is_ready = len(all_specialists) > 0
        if st.button("🚀 Start Board Review", type="primary", use_container_width=True, disabled=not is_ready):
            _run_analysis()

        if st.button("⬅️ Back to Team Selection", use_container_width=True):
            state_manager.prev_step()
        return

    # Results available
    result = state_manager.crew_result
    board_report, minimal_changes, final_cv, cover_letter = _extract_outputs(result)
    _save_to_history(board_report, minimal_changes, final_cv, cover_letter)

    st.success("Analysis Complete!")

    usage = st.session_state.get("token_usage")
    if usage and usage.get("total_tokens"):
        st.caption(
            f"🔢 Tokens used: {usage.get('total_tokens', 0):,} "
            f"(prompt: {usage.get('prompt_tokens', 0):,}, completion: {usage.get('completion_tokens', 0):,})"
        )

    tab_names = ["📋 Board Report", "🛠️ Minimal Changes", "📊 ATS Score", "📄 Final CV"]
    if cover_letter:
        tab_names.append("✉️ Cover Letter")
    tab_names.append("🎤 Interview Prep")
    tabs = st.tabs(tab_names)

    with tabs[0]:
        st.markdown(board_report)

    with tabs[1]:
        st.info("Specific keywords and phrasing tweaks identified by the board.")
        st.markdown(minimal_changes)

    with tabs[2]:
        _render_ats_tab(final_cv)

    with tabs[3]:
        pdf_bytes = CVService.generate_pdf(final_cv)
        docx_bytes = CVService.generate_docx(final_cv)
        col1, col2 = st.columns(2)
        if pdf_bytes:
            col1.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name="Optimized_CV.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        if docx_bytes:
            col2.download_button(
                label="📥 Download DOCX",
                data=docx_bytes,
                file_name="Optimized_CV.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

        st.error(
            "⚠️ **CRITICAL WARNING:** The AI may suggest skills or experiences you **do not possess**. "
            "Review every change carefully. Including false information in your CV can have serious consequences. "
            "Ensure all content aligns with your actual experience."
        )

        st.info("💡 **Note:** The text below is a preview. The downloaded files have professional formatting.")
        st.markdown(final_cv)

        st.caption("👉 For a full rewrite tailored to your interview answers, use the **Personalize** step below.")

    next_tab = 4
    if cover_letter:
        with tabs[next_tab]:
            st.markdown(cover_letter)
            cover_pdf = CVService.generate_pdf(cover_letter)
            if cover_pdf:
                st.download_button(
                    label="📥 Download Cover Letter PDF",
                    data=cover_pdf,
                    file_name="Cover_Letter.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        next_tab += 1

    with tabs[next_tab]:
        _render_interview_prep_tab(board_report)

    st.write("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🏠 Start Over", use_container_width=True):
            state_manager.reset()
    with col2:
        if st.button("⬅️ Step Back", use_container_width=True):
            state_manager.crew_result = None
            st.rerun()
    with col3:
        if st.button("✨ Personalize ➡️", type="primary", use_container_width=True):
            state_manager.next_step()
