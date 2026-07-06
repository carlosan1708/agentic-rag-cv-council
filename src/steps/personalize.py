"""Module for rendering the personalization/interview step in the application."""

import streamlit as st

from logger import logger
from services.analysis_service import AnalysisService
from services.persona_service import PersonaService
from state_manager import state_manager


def render_personalize_step():
    """Render the personalization interview step UI."""
    st.header("Step 6: Board Interview")

    if st.session_state.get("demo_mode"):
        from ui_components import render_demo_lock

        render_demo_lock("The Board Interview (personalized CV rewrite from your answers)")
        if st.button("⬅️ Back to Results"):
            state_manager.step = 5
            st.rerun()
        return
    st.markdown("""
        The Board of Advisors can rewrite your CV into a professional, modern format.
        To make it truly impactful, they need to clarify a few details about your real-world achievements.
    """)

    with st.container(border=True):
        if not st.session_state.interview_questions:
            if st.button("🎤 Generate Questions", use_container_width=True, type="primary"):
                with st.spinner("Board is reviewing documents..."):
                    try:
                        st.session_state.interview_questions = AnalysisService.generate_interview_questions(
                            cv_content=st.session_state.cv_content,
                            config=state_manager.config,
                        )
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Question generation failed: {e}")
                        st.error(f"Could not generate questions: {e}")
        else:
            with st.form("interview_form_step6"):
                for i, q in enumerate(st.session_state.interview_questions):
                    st.markdown(f"**{q}**")
                    st.session_state.user_answers[f"q_{i}"] = st.text_area(
                        f"Your Answer {i + 1}", key=f"ans_step6_{i}", height=100
                    )

                if st.form_submit_button("✨ Generate Optimized CV ➡️", use_container_width=True, type="primary"):
                    with st.spinner("Board is incorporating your answers..."):
                        combined_answers = "\n".join(
                            [
                                f"Q: {q}\nA: {st.session_state.user_answers.get(f'q_{i}', '')}"
                                for i, q in enumerate(st.session_state.interview_questions)
                            ]
                        )
                        available_personas = PersonaService.load_personas()
                        selected_personas = [
                            available_personas[name]
                            for name in state_manager.selected_persona_names
                            if name in available_personas
                        ]

                        crew = AnalysisService.create_analysis_crew(
                            selected_personas=selected_personas,
                            cv_content=st.session_state.cv_content,
                            job_description=state_manager.job.description,
                            config=state_manager.config,
                            user_answers=combined_answers,
                            include_cover_letter=st.session_state.get("generate_cover_letter", False),
                            debate_mode=st.session_state.get("debate_mode", False),
                        )
                        state_manager.crew_result = AnalysisService.kickoff_with_retry(crew)
                        st.session_state.token_usage = AnalysisService.get_token_usage(state_manager.crew_result)
                        st.session_state.interview_done = True
                        st.session_state.history_saved = False
                        state_manager.step = 5  # Back to results
                        st.rerun()

            if st.button("Cancel & Return"):
                st.session_state.step = 5
                st.rerun()

    if st.button("⬅️ Back"):
        st.session_state.step = 5
        st.rerun()
