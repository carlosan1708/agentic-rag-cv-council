"""Module for rendering the welcome step in the application."""

import streamlit as st

from services.history_service import HistoryService
from state_manager import state_manager


def _render_history():
    """Lists locally persisted past analyses."""
    records = HistoryService.list_analyses()
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
                    HistoryService.delete_analysis(record.id)
                    st.rerun()
                if st.session_state.get(f"show_record_{record.id}"):
                    tabs = st.tabs(["📋 Board Report", "🛠️ Minimal Changes", "📄 Final CV"])
                    tabs[0].markdown(record.board_report or "_empty_")
                    tabs[1].markdown(record.minimal_changes or "_empty_")
                    tabs[2].markdown(record.final_cv or "_empty_")

        if st.button("🧹 Delete all my data", use_container_width=True):
            HistoryService.delete_all()
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

    st.info("💡 **Steps:** Configuration -> Upload -> Job -> Team -> Results.", icon="ℹ️")

    if st.button("Get Started ➡️", use_container_width=True, type="primary"):
        state_manager.next_step()

    _render_history()
