"""Job Tracker page: dashboard, kanban board, timelines and CV versions per application.

Designed to stay responsive with hundreds of applications: records are loaded
once per rerun (cached in session state, invalidated on any mutation), the list
is searchable/filterable/sortable and paginated, board columns are capped with a
"show all" per column, and per-CV PDF/DOCX generation is lazy (only on request).
"""

import streamlit as st

from services.analysis_service import AnalysisService
from services.config_service import ConfigService
from services.cv_service import CVService
from services.tracker_service import (
    EVENT_ICONS,
    EVENT_TYPES,
    STATUS_ICONS,
    STATUSES,
    TrackerService,
    format_timeline,
)
from state_manager import state_manager
from ui_components import render_demo_lock

PAGE_SIZE = 10
BOARD_CARD_CAP = 20  # cards shown per board column before "show all"
SORT_MODES = ["Newest first", "Oldest first", "Company A-Z", "ATS score"]

_CACHE_KEY = "tracker_records_cache"


def _owner() -> str:
    return st.session_state.history_owner


def _load_records():
    """Loads the owner's applications once per rerun (cached; invalidated on mutation)."""
    if _CACHE_KEY not in st.session_state:
        st.session_state[_CACHE_KEY] = TrackerService.list_applications(owner=_owner())
    return st.session_state[_CACHE_KEY]


def _invalidate():
    """Drops the cached record list so the next load reads fresh from storage."""
    st.session_state.pop(_CACHE_KEY, None)


def _reload_and_rerun():
    _invalidate()
    st.rerun()


def _llm_ready() -> bool:
    """True when a provider/model is configured (API key, or keyless Ollama)."""
    config = state_manager.config
    if not config.selected_model or config.selected_model == "demo":
        return False
    return bool(config.api_key) or not ConfigService.requires_api_key(config.llm_provider)


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


def _render_stale_nudges(records):
    """Active applications with no activity for a while - nudge a follow-up."""
    stale = TrackerService.stale_applications(records)
    if not stale:
        return

    plural = "s" if len(stale) > 1 else ""
    with st.expander(f"⏰ {len(stale)} application{plural} may need a follow-up (no activity in 7+ days)", expanded=False):
        for record, days_stale in stale:
            with st.container(border=True):
                info_col, draft_col, log_col = st.columns([3, 1, 1])
                info_col.markdown(
                    f"{STATUS_ICONS.get(record.status, '📄')} **{record.company}** · {record.job_title} - "
                    f"no activity for **{days_stale} days**"
                )
                if draft_col.button("✉️ Draft follow-up", key=f"draft_{record.id}", use_container_width=True):
                    st.session_state[f"show_draft_{record.id}"] = not st.session_state.get(f"show_draft_{record.id}", False)
                if log_col.button(
                    "✅ Log sent",
                    key=f"log_followup_{record.id}",
                    use_container_width=True,
                    help="Adds a 'Follow-up' timeline entry",
                ):
                    TrackerService.add_event(record.id, "Follow-up", "Follow-up email sent.", owner=_owner())
                    _reload_and_rerun()
                if st.session_state.get(f"show_draft_{record.id}"):
                    st.code(TrackerService.follow_up_draft(record), language=None)


def _render_cv_diff(records):
    """Compare the CV versions used across applications."""
    with_cv = [r for r in records if r.cv_markdown]
    if len(with_cv) < 2:
        return

    with st.expander("🔍 Compare CV versions", expanded=False):
        st.caption("See exactly what changed between the CVs you sent to different companies.")
        labels = {f"{r.company} · {r.job_title} ({r.created_at})": r for r in with_cv}
        names = list(labels)
        col_a, col_b = st.columns(2)
        pick_a = col_a.selectbox("Version A", names, index=0, key="diff_a")
        pick_b = col_b.selectbox("Version B", names, index=1, key="diff_b")

        diff = CVService.markdown_diff(labels[pick_a].cv_markdown, labels[pick_b].cv_markdown, pick_a, pick_b)
        if diff:
            st.code(diff, language="diff")
        else:
            st.success("These two CV versions are identical.")


def _render_next_round_prep(record):
    """AI prep for the next round, informed by this application's timeline."""
    st.markdown("**🎤 Next round**")
    prep_key = f"next_prep_{record.id}"

    if st.session_state.get(prep_key):
        st.markdown(st.session_state[prep_key])
        col_dl, col_redo = st.columns(2)
        col_dl.download_button(
            "⬇️ Download prep",
            st.session_state[prep_key],
            f"Interview_prep_{record.company or record.id}.md",
            mime="text/markdown",
            key=f"dl_prep_{record.id}",
            use_container_width=True,
        )
        if col_redo.button("🔄 Regenerate", key=f"redo_prep_{record.id}", use_container_width=True):
            st.session_state[prep_key] = ""
            st.rerun()
        return

    if st.button(
        "🎤 Prep me for the next round",
        key=f"prep_{record.id}",
        use_container_width=True,
        help="Uses this application's timeline (interviews, feedback) plus the CV and job.",
    ):
        if not _llm_ready():
            st.warning("Configure an AI provider first (Get Started → Step 1) - the prep uses your own model/key.")
            return
        with st.spinner("Reading the timeline and preparing you..."):
            try:
                prep = AnalysisService.generate_next_round_prep(
                    cv_markdown=record.cv_markdown or "(no CV stored)",
                    job_snippet=record.job_snippet,
                    timeline=format_timeline(record),
                    config=state_manager.config,
                )
                st.session_state[prep_key] = CVService.clean_markdown_code_blocks(prep)
                st.rerun()
            except Exception as e:
                st.error(f"Could not generate prep: {e}")


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
                    _reload_and_rerun()
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
                    _reload_and_rerun()
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
                _reload_and_rerun()
            else:
                st.warning("Write what happened before adding the entry.")


def _render_cv_downloads(record):
    """Lazily generates CV PDF/DOCX only when the user asks (kept cheap at scale)."""
    st.markdown(f"**CV version used** (as of {record.created_at}):")
    if not st.toggle("📄 Prepare CV downloads", key=f"prep_cv_{record.id}"):
        st.caption("Toggle to generate the PDF/DOCX of this CV version.")
        return

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
            _reload_and_rerun()

        with st.expander("Details, timeline & CV version used"):
            if record.job_snippet:
                st.markdown(f"**Job:** {record.job_snippet}")

            _render_timeline(record)
            st.markdown("---")
            _render_next_round_prep(record)
            st.markdown("---")

            notes = st.text_area("General notes", value=record.notes, key=f"notes_{record.id}", height=80)
            col_save, col_delete = st.columns([1, 1])
            if col_save.button("💾 Save notes", key=f"save_notes_{record.id}"):
                TrackerService.update_application(record.id, owner=_owner(), notes=notes)
                _invalidate()
                st.toast("Notes saved", icon="💾")
            if col_delete.button("🗑️ Delete application", key=f"delete_app_{record.id}"):
                TrackerService.delete_application(record.id, owner=_owner())
                _reload_and_rerun()

            if record.cv_markdown:
                st.markdown("---")
                _render_cv_downloads(record)
                if st.toggle("👁️ Preview this CV version", key=f"preview_cv_{record.id}"):
                    st.markdown(record.cv_markdown)
            else:
                st.caption("No CV version stored for this application.")

            if record.cover_letter:
                if st.toggle("✉️ Show cover letter used", key=f"preview_cl_{record.id}"):
                    st.markdown(record.cover_letter)


def _render_filters(records):
    """Search + status filter + sort row. Returns the filtered, sorted record list."""
    search_col, sort_col = st.columns([3, 2])
    query = search_col.text_input(
        "Search", placeholder="Search company or job title...", key="tracker_search", label_visibility="collapsed"
    )
    sort_mode = sort_col.selectbox("Sort", SORT_MODES, key="tracker_sort", label_visibility="collapsed")

    selected_statuses = st.multiselect(
        "Filter by status",
        STATUSES,
        default=[],
        key="tracker_status_filter",
        label_visibility="collapsed",
        placeholder="Filter by status (all)",
    )
    statuses = selected_statuses or None

    filtered = TrackerService.filter_records(records, query=query, statuses=statuses)
    return TrackerService.sort_records(filtered, sort_mode)


def _render_list(records):
    """Paginated application list (only the current page renders its widgets)."""
    total = len(records)
    if total == 0:
        st.info("No applications match your search/filter.")
        return

    page_count = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page = min(st.session_state.get("tracker_page", 0), page_count - 1)

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    st.caption(f"Showing {start + 1}–{end} of {total} applications")

    for record in records[start:end]:
        _render_application(record)

    if page_count > 1:
        prev_col, mid_col, next_col = st.columns([1, 2, 1])
        if prev_col.button("⬅️ Previous", disabled=page <= 0, use_container_width=True):
            st.session_state["tracker_page"] = page - 1
            st.rerun()
        mid_col.markdown(
            f"<div style='text-align:center;padding-top:6px;'>Page {page + 1} of {page_count}</div>",
            unsafe_allow_html=True,
        )
        if next_col.button("Next ➡️", disabled=page >= page_count - 1, use_container_width=True):
            st.session_state["tracker_page"] = page + 1
            st.rerun()


def _render_board(records):
    """Kanban board: one column per status, cards move with the arrow buttons.

    (Streamlit has no native drag-and-drop; moves also log a timeline entry.)
    Columns are capped at BOARD_CARD_CAP cards with a per-column "show all" so the
    board stays responsive even with hundreds of applications.
    """
    columns = st.columns(len(STATUSES))
    for index, status in enumerate(STATUSES):
        with columns[index]:
            in_status = [r for r in records if r.status == status]
            st.markdown(f"**{STATUS_ICONS[status]} {status}** · {len(in_status)}")

            show_all_key = f"board_all_{status}"
            visible = in_status
            capped = len(in_status) > BOARD_CARD_CAP and not st.session_state.get(show_all_key)
            if capped:
                visible = in_status[:BOARD_CARD_CAP]

            for record in visible:
                with st.container(border=True):
                    st.markdown(f"**{record.company}**")
                    st.caption(record.job_title)
                    if record.ats_score is not None:
                        st.caption(f"ATS {record.ats_score}/100")
                    left_col, right_col = st.columns(2)
                    if index > 0:
                        if left_col.button(
                            "◀", key=f"left_{record.id}", help=f"Move to {STATUSES[index - 1]}", use_container_width=True
                        ):
                            TrackerService.update_application(record.id, owner=_owner(), status=STATUSES[index - 1])
                            _reload_and_rerun()
                    if index < len(STATUSES) - 1:
                        if right_col.button(
                            "▶", key=f"right_{record.id}", help=f"Move to {STATUSES[index + 1]}", use_container_width=True
                        ):
                            TrackerService.update_application(record.id, owner=_owner(), status=STATUSES[index + 1])
                            _reload_and_rerun()

            if capped:
                if st.button(f"Show all {len(in_status)}", key=f"show_all_{status}", use_container_width=True):
                    st.session_state[show_all_key] = True
                    st.rerun()


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

    records = _load_records()

    if not records:
        st.info(
            "No applications tracked yet. Run a board review and click **📌 Track this application** "
            "on the results screen - the exact CV version you applied with is stored alongside the job."
        )
        _render_manual_add()
        return

    _render_dashboard(records)
    _render_stale_nudges(records)
    st.write("---")

    view_mode = st.radio("View", ["📄 List", "🗂️ Board"], horizontal=True, label_visibility="collapsed", key="tracker_view")

    _render_manual_add()
    _render_cv_diff(records)

    # Search / filter / sort apply to both views; large trackers stay navigable.
    visible = _render_filters(records)

    if view_mode == "🗂️ Board":
        _render_board(visible)
    else:
        _render_list(visible)

    st.download_button(
        "⬇️ Export tracker as CSV",
        TrackerService.to_csv(records),
        "job_tracker.csv",
        mime="text/csv",
        use_container_width=True,
    )
