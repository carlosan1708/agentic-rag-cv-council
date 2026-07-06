"""Job Tracker page: dashboard + applications with the CV version used to apply."""

import streamlit as st

from services.cv_service import CVService
from services.tracker_service import EVENT_ICONS, EVENT_TYPES, STATUS_ICONS, STATUSES, TrackerService
from ui_components import render_demo_lock


def _owner() -> str:
    return st.session_state.history_owner


def _render_dashboard(records):
    """KPI tiles + status breakdown. Identity is carried by label/icon (never color
    alone); the applications list below doubles as the table view."""
    stats = TrackerService.stats(records)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Applications", stats.total)
    col2.metric("Active", stats.active, help="Applied or interviewing")
    col3.metric("Interviews", stats.interviews)
    col4.metric("Offers", stats.offers)
    col5.metric(
        "Response rate",
        f"{round(stats.response_rate * 100)}%" if stats.response_rate is not None else "—",
        help="Companies that responded (interview, offer or rejection) out of submitted applications",
    )
    if stats.avg_ats is not None:
        st.caption(f"📊 Average ATS score of tracked CV versions: **{stats.avg_ats:.0f}/100**")

    st.markdown("**Pipeline**")
    max_count = max(stats.by_status.values()) or 1
    for status in STATUSES:
        count = stats.by_status[status]
        label_col, bar_col = st.columns([1, 4])
        label_col.markdown(f"{STATUS_ICONS[status]} {status} · **{count}**")
        bar_col.progress(count / max_count)


def _render_manual_add():
    """Track a job applied to outside the app."""
    with st.expander("➕ Add an application manually", expanded=False):
        st.caption("Track jobs you applied to outside this app - the CV text is optional.")
        with st.form("manual_add_form", clear_on_submit=True):
            company = st.text_input("Company")
            job_title = st.text_input("Job title")
            status = st.selectbox("Status", STATUSES, index=STATUSES.index("Applied"))
            notes = st.text_area("Notes (optional)", height=80)
            cv_markdown = st.text_area("CV version used (optional, paste text/markdown)", height=120)
            if st.form_submit_button("Add to tracker", type="primary"):
                if company.strip() and job_title.strip():
                    TrackerService.add_application(
                        company=company,
                        job_title=job_title,
                        status=status,
                        notes=notes,
                        cv_markdown=cv_markdown,
                        owner=_owner(),
                    )
                    st.rerun()
                else:
                    st.warning("Company and job title are required.")


def _render_timeline(record):
    """Activity timeline: interview notes, recruiter calls, feedback, status changes."""
    st.markdown("**📅 Activity timeline**")

    if record.events:
        for event in sorted(record.events, key=lambda e: e.get("id", 0), reverse=True):
            icon = EVENT_ICONS.get(event.get("type", ""), "🗒️")
            entry_col, delete_col = st.columns([8, 1])
            entry_col.markdown(
                f"{icon} **{event.get('type', 'Note')}** · <small>{event.get('created_at', '')}</small>\n\n"
                f"{event.get('content', '')}",
                unsafe_allow_html=True,
            )
            if event.get("type") != "Status change":
                if delete_col.button("🗑️", key=f"del_event_{record.id}_{event.get('id')}", help="Delete entry"):
                    TrackerService.delete_event(record.id, event.get("id"), owner=_owner())
                    st.rerun()
    else:
        st.caption("Nothing logged yet - record interviews, recruiter calls, feedback or follow-ups below.")

    with st.form(f"add_event_form_{record.id}", clear_on_submit=True):
        type_col, content_col = st.columns([1, 3])
        entry_type = type_col.selectbox("Type", EVENT_TYPES, key=f"event_type_{record.id}")
        content = content_col.text_area(
            "What happened?",
            key=f"event_content_{record.id}",
            height=80,
            placeholder="e.g., 'System design interview with the platform team. Asked about rate limiting and "
            "K8s autoscaling. Follow-up scheduled for Tuesday. Interviewer: Dana (eng manager).'",
        )
        if st.form_submit_button("➕ Add to timeline"):
            if TrackerService.add_event(record.id, entry_type, content, owner=_owner()):
                st.rerun()
            else:
                st.warning("Write what happened before adding the entry.")


def _render_application(record):
    header = f"{STATUS_ICONS.get(record.status, '📄')} **{record.company}** · {record.job_title}"
    score = f" · ATS {record.ats_score}/100" if record.ats_score is not None else ""

    with st.container(border=True):
        info_col, status_col = st.columns([3, 1])
        info_col.markdown(f"{header}\n\n<small>Applied: {record.created_at}{score}</small>", unsafe_allow_html=True)

        new_status = status_col.selectbox(
            "Status",
            STATUSES,
            index=STATUSES.index(record.status) if record.status in STATUSES else 1,
            key=f"status_{record.id}",
            label_visibility="collapsed",
        )
        if new_status != record.status:
            TrackerService.update_application(record.id, owner=_owner(), status=new_status)
            st.rerun()

        with st.expander("Details, timeline & CV version used"):
            if record.job_snippet:
                st.markdown(f"**Job:** {record.job_snippet}")

            _render_timeline(record)
            st.markdown("---")

            notes = st.text_area("General notes", value=record.notes, key=f"notes_{record.id}", height=80)
            col_save, col_delete = st.columns([1, 1])
            if col_save.button("💾 Save notes", key=f"save_notes_{record.id}"):
                TrackerService.update_application(record.id, owner=_owner(), notes=notes)
                st.toast("Notes saved", icon="💾")
            if col_delete.button("🗑️ Delete application", key=f"delete_app_{record.id}"):
                TrackerService.delete_application(record.id, owner=_owner())
                st.rerun()

            if record.cv_markdown:
                st.markdown("---")
                st.markdown(f"**CV version used** (as of {record.created_at}):")
                pdf_col, docx_col = st.columns(2)
                pdf_bytes = CVService.generate_pdf(record.cv_markdown)
                docx_bytes = CVService.generate_docx(record.cv_markdown)
                if pdf_bytes:
                    pdf_col.download_button(
                        "📥 CV PDF",
                        pdf_bytes,
                        f"CV_{record.company or record.id}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{record.id}",
                        use_container_width=True,
                    )
                if docx_bytes:
                    docx_col.download_button(
                        "📥 CV DOCX",
                        docx_bytes,
                        f"CV_{record.company or record.id}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"docx_{record.id}",
                        use_container_width=True,
                    )
                if st.toggle("👁️ Preview this CV version", key=f"preview_cv_{record.id}"):
                    st.markdown(record.cv_markdown)
            else:
                st.caption("No CV version stored for this application.")

            if record.cover_letter:
                if st.toggle("✉️ Show cover letter used", key=f"preview_cl_{record.id}"):
                    st.markdown(record.cover_letter)


def render_tracker_page():
    """Renders the full-page Job Tracker (full version only)."""
    col_title, col_back = st.columns([3, 1])
    col_title.subheader("📋 Job Tracker")
    if col_back.button("⬅️ Back to app", use_container_width=True):
        st.session_state.view = "wizard"
        st.rerun()

    if st.session_state.get("demo_mode"):
        render_demo_lock("The Job Tracker")
        return

    records = TrackerService.list_applications(owner=_owner())

    if not records:
        st.info(
            "No applications tracked yet. Run a board review and click **📌 Track this application** "
            "on the results screen - the exact CV version you applied with is stored alongside the job."
        )
        _render_manual_add()
        return

    _render_dashboard(records)
    st.write("---")
    _render_manual_add()

    for record in records:
        _render_application(record)

    st.download_button(
        "⬇️ Export tracker as CSV",
        TrackerService.to_csv(records),
        "job_tracker.csv",
        mime="text/csv",
        use_container_width=True,
    )
