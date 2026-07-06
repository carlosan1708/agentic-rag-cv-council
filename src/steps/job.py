"""Module for rendering the job target step in the application."""

import streamlit as st

from services.ats_service import ATSService
from services.job_service import JobService
from state_manager import state_manager
from ui_components import render_demo_banner, render_demo_lock


def _render_multi_job_compare():
    """Instant ATS comparison of the uploaded CV against multiple job descriptions."""
    with st.expander("⚖️ Not sure which job to target? Compare multiple jobs", expanded=False):
        st.caption(
            "Paste several job descriptions and get an instant, deterministic match score for each "
            "(keyword & structure analysis - no AI tokens used)."
        )

        label = st.text_input("Job label", placeholder="e.g., 'Backend Engineer @ Acme'", key="compare_label")
        description = st.text_area("Job description", height=150, key="compare_description")
        if st.button("➕ Add job to comparison"):
            if label and description:
                st.session_state.compare_jobs.append({"label": label, "description": description})
                st.rerun()
            else:
                st.warning("Both a label and a description are required.")

        if not st.session_state.compare_jobs:
            return

        rows = []
        for job in st.session_state.compare_jobs:
            report = ATSService.score_cv(st.session_state.cv_content, job["description"])
            rows.append(
                {
                    "Job": job["label"],
                    "Match Score": f"{report.score}/100",
                    "Keyword Coverage": f"{round(report.keyword_coverage * 100)}%",
                    "Top Missing Keywords": ", ".join(report.missing_keywords[:5]) or "-",
                }
            )
        st.dataframe(rows, use_container_width=True)

        cols = st.columns(len(st.session_state.compare_jobs) + 1)
        for idx, job in enumerate(st.session_state.compare_jobs):
            if cols[idx].button(f"🎯 Target '{job['label']}'", key=f"target_{idx}"):
                state_manager.update_job(description=job["description"])
                st.rerun()
        if cols[-1].button("🗑️ Clear list"):
            st.session_state.compare_jobs = []
            st.rerun()


def render_job_step():
    """Render the job target step UI."""
    st.subheader("Step 3: Target Job Context")

    if st.session_state.get("demo_mode"):
        if render_demo_banner():
            state_manager.reset()
        render_demo_lock("Job-posting URL extraction and multi-job comparison")
        st.markdown("**Sample job posting used by the demo:**")
        st.text_area("Sample job", state_manager.job.description, height=260, disabled=True, label_visibility="collapsed")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back", use_container_width=True):
                state_manager.prev_step()
        with col2:
            if st.button("Next: Assemble Board ➡️", type="primary", use_container_width=True):
                state_manager.next_step()
        return

    job = state_manager.job

    def handle_scrape():
        url = st.session_state.job_url_input
        if url:
            with st.spinner("Extracting job description..."):
                try:
                    content = JobService.scrape_job(url)
                    state_manager.update_job(url=url, description=content)
                    st.success("Successfully extracted the job description!")
                except Exception as e:
                    st.error(f"Failed to extract job: {str(e)}")
        else:
            st.warning("Please enter a job posting URL first.")

    def on_text_change():
        text = st.session_state.job_text_input
        if text != job.description:
            state_manager.update_job(description=text)

    with st.container(border=True):
        st.markdown("**Option 1: Paste a job posting URL** (LinkedIn, Indeed, Greenhouse, Lever, ...)")
        url_col, btn_col = st.columns([4, 1])
        with url_col:
            st.text_input(
                "Job posting URL",
                placeholder="https://www.linkedin.com/jobs/view/...",
                key="job_url_input",
                value=job.url,
                label_visibility="collapsed",
            )
        with btn_col:
            st.button("Extract 🔍", on_click=handle_scrape, use_container_width=True)

        st.markdown("**Option 2: Paste Job Description**")
        st.text_area(
            "Job Description Text",
            height=200,
            placeholder="Paste the full job description here...",
            key="job_text_input",
            on_change=on_text_change,
            value=job.description,
        )

    _render_multi_job_compare()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            state_manager.prev_step()
    with col2:
        disabled = not job.description
        if st.button("Next: Assemble Board ➡️", type="primary", disabled=disabled, use_container_width=True):
            state_manager.next_step()
