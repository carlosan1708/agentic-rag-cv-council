"""Module for rendering the welcome step in the application."""

import streamlit as st

import demo_data
from services.history_service import HistoryService
from state_manager import state_manager


def _render_history():
    """Lists locally persisted past analyses."""
    owner = st.session_state.history_owner
    records = HistoryService.list_analyses(owner=owner)
    if not records:
        return

    with st.expander(f"📜 Previous Analyses ({len(records)})", expanded=False):
        st.caption("Stored locally on this machine only. You can delete everything at any time.")
        for record in records:
            score = f" · ATS {record.ats_score}/100" if record.ats_score is not None else ""
            title = record.job_snippet[:80] or "(no job description)"
            with st.container(border=True):
                st.markdown(f"**#{record.id}** · {record.created_at}{score}\n\n{title}")
                col1, col2 = st.columns([1, 1])
                if col1.button("👁️ View", key=f"view_{record.id}"):
                    st.session_state[f"show_record_{record.id}"] = not st.session_state.get(f"show_record_{record.id}", False)
                if col2.button("🗑️ Delete", key=f"del_hist_{record.id}"):
                    HistoryService.delete_analysis(record.id, owner=owner)
                    st.rerun()
                if st.session_state.get(f"show_record_{record.id}"):
                    tabs = st.tabs(["📋 Board Report", "🛠️ Minimal Changes", "📄 Final CV"])
                    tabs[0].markdown(record.board_report or "_empty_")
                    tabs[1].markdown(record.minimal_changes or "_empty_")
                    tabs[2].markdown(record.final_cv or "_empty_")

        if st.button("🧹 Delete all my data", use_container_width=True):
            HistoryService.delete_all(owner=owner)
            st.rerun()


def render_welcome_step():
    """Render the welcome screen UI."""
    st.markdown(
        """
        <div style="text-align: center; padding-top: 5px;">
            <span style="background-color: #e1f5fe; color: #01579b; padding: 2px 10px; border-radius: 16px; font-size: 0.7rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">MVP Version</span>
            <h2 style="margin-top: 5px; margin-bottom: 0;">🚀 Elevate Your Career with AI</h2>
            <p style="font-size: 1rem; color: #555;">
                Expert feedback and high-impact CVs tailored to your dream job.
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### 👤 **The Board**")
        st.write("Assemble AI experts: Tech Recruiters to Startup Founders.")

    with col2:
        st.markdown("##### 🔍 **Critique**")
        st.write("Deep analysis, ATS scoring, cover letters and interview prep.")

    with col3:
        st.markdown("##### ✨ **Personalized**")
        st.write("Optional AI interview to inject real achievements.")

    st.info("💡 **Steps:** Setup → Upload → Job → Team → Results (+ optional Polish).", icon="ℹ️")

    col_start, col_demo = st.columns(2)
    with col_start:
        if st.button("Get Started ➡️", use_container_width=True, type="primary"):
            state_manager.next_step()
    with col_demo:
        if st.button(
            "🎮 Try the Demo", use_container_width=True, help="Sample CV and job, instant canned results - no API key needed."
        ):
            start_demo()

    _render_history()


def start_demo():
    """Preloads the sample candidate and jumps straight to team selection."""
    state_manager.ensure_initialized()
    st.session_state.demo_mode = True
    st.session_state.cv_content = demo_data.DEMO_CV
    st.session_state.cv_filename = demo_data.DEMO_CV_FILENAME
    state_manager.update_job(description=demo_data.DEMO_JOB)
    state_manager.update_config(selected_model="demo", api_key="demo")
    state_manager.step = 4
    st.rerun()
