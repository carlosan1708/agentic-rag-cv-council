"""E2E: job tracker page, dashboard and manual application entry."""

from conftest import fill_input
from playwright.sync_api import expect


def _open_tracker(page, url):
    page.goto(url)
    page.get_by_role("button", name="📋 Job Tracker - your applications & CV versions").click()
    page.get_by_text("📋 Job Tracker").wait_for()


def test_tracker_opens_with_empty_state(page, app_url):
    _open_tracker(page, app_url)
    expect(page.get_by_text("No applications tracked yet", exact=False)).to_be_visible()
    expect(page.get_by_text("Add an application manually")).to_be_visible()


def test_manual_add_updates_dashboard(page, app_url):
    _open_tracker(page, app_url)
    page.get_by_text("Add an application manually").click()
    fill_input(page, "Company", "Acme Corp")
    fill_input(page, "Job title", "Platform Engineer")
    page.get_by_role("button", name="Add to tracker").click()

    # Dashboard KPI tiles appear with the new application
    expect(page.get_by_text("Applications", exact=True)).to_be_visible()
    expect(page.get_by_text("Acme Corp").first).to_be_visible()
    expect(page.get_by_text("Platform Engineer").first).to_be_visible()
    expect(page.get_by_text("Pipeline")).to_be_visible()
    expect(page.get_by_role("button", name="⬇️ Export tracker as CSV")).to_be_visible()


def test_tracker_application_can_be_deleted(page, app_url):
    _open_tracker(page, app_url)
    page.get_by_text("Add an application manually").click()
    fill_input(page, "Company", "DeleteMe Inc")
    fill_input(page, "Job title", "Temp Role")
    page.get_by_role("button", name="Add to tracker").click()
    expect(page.get_by_text("DeleteMe Inc").first).to_be_visible()

    page.get_by_text("Details, timeline & CV version used").first.click()
    page.get_by_role("button", name="🗑️ Delete application").first.click()
    expect(page.get_by_text("DeleteMe Inc")).not_to_be_visible()


def test_back_button_returns_to_welcome(page, app_url):
    _open_tracker(page, app_url)
    page.get_by_role("button", name="⬅️ Back to app").click()
    expect(page.get_by_text("Elevate Your Career with AI")).to_be_visible()


def test_tracker_save_locked_in_demo_results(page, app_url):
    from conftest import run_demo_analysis

    run_demo_analysis(page, app_url)
    expect(page.get_by_text("Job Tracker", exact=False).first).to_be_visible()
    expect(page.get_by_text("available in the full version", exact=False).first).to_be_visible()
    # The tracker-save expander itself is not offered in demo
    expect(page.get_by_text("Track this application (stores this CV version)")).not_to_be_visible()


def test_timeline_entry_can_be_added(page, app_url):
    _open_tracker(page, app_url)
    page.get_by_text("Add an application manually").click()
    fill_input(page, "Company", "Timeline Corp")
    fill_input(page, "Job title", "Notes Engineer")
    page.get_by_role("button", name="Add to tracker").click()
    expect(page.get_by_text("Timeline Corp").first).to_be_visible()

    page.get_by_text("Details, timeline & CV version used").first.click()
    expect(page.get_by_text("Activity timeline").first).to_be_visible()

    # Multiple application cards may be present (shared test server) - use the first (newest)
    field = page.get_by_label("What happened?").first
    field.fill("Phone screen with recruiter - salary range discussed.")
    field.press("Tab")
    page.get_by_role("button", name="➕ Add to timeline").first.click()
    expect(page.get_by_text("Phone screen with recruiter", exact=False).first).to_be_visible()


def test_details_with_stored_cv_render_without_error(page, app_url):
    """Regression: nested expanders crashed the details view for applications with a CV."""
    _open_tracker(page, app_url)
    page.get_by_text("Add an application manually").click()
    fill_input(page, "Company", "CVStore GmbH")
    fill_input(page, "Job title", "Archivist")
    fill_input(page, "CV version used (optional, paste text/markdown)", "# My CV\n- Did things")
    page.get_by_role("button", name="Add to tracker").click()
    expect(page.get_by_text("CVStore GmbH").first).to_be_visible()

    page.get_by_text("Details, timeline & CV version used").first.click()
    expect(page.get_by_text("StreamlitAPIException")).not_to_be_visible()

    # CV downloads are generated lazily behind a toggle (cheap at scale)
    page.get_by_text("📄 Prepare CV downloads").first.click()
    expect(page.get_by_role("button", name="📥 CV PDF").first).to_be_visible()

    page.get_by_text("👁️ Preview this CV version").first.click()
    expect(page.get_by_text("Did things").first).to_be_visible()


def test_board_view_and_card_move(page, app_url):
    _open_tracker(page, app_url)
    page.get_by_text("Add an application manually").click()
    fill_input(page, "Company", "Kanban Co")
    fill_input(page, "Job title", "Board Engineer")
    page.get_by_role("button", name="Add to tracker").click()
    expect(page.get_by_text("Kanban Co").first).to_be_visible()

    page.get_by_text("🗂️ Board").click()
    # Columns for every status are shown
    for status in ("Saved", "Applied", "Interviewing", "Offer", "Rejected"):
        expect(page.get_by_text(status, exact=False).first).to_be_visible()

    # Move the newest card one column to the right (Applied -> Interviewing)
    page.get_by_role("button", name="▶").first.click()
    expect(page.get_by_text("Kanban Co").first).to_be_visible()

    # The move is recorded in the timeline (visible in list view)
    page.get_by_text("📄 List").click()
    page.get_by_text("Details, timeline & CV version used").first.click()
    expect(page.get_by_text("Applied → Interviewing").first).to_be_visible()


def test_cv_diff_between_versions(page, app_url):
    _open_tracker(page, app_url)
    # Two applications with different CV texts
    for company, cv_line in (("DiffCo A", "- Docker expert"), ("DiffCo B", "- Kubernetes expert")):
        page.get_by_text("Add an application manually").click()
        fill_input(page, "Company", company)
        fill_input(page, "Job title", "Engineer")
        fill_input(page, "CV version used (optional, paste text/markdown)", f"# CV\n{cv_line}")
        page.get_by_role("button", name="Add to tracker").click()
        # exact match hits the visible card header, not hidden diff-selector options
        expect(page.get_by_text(company, exact=True).first).to_be_visible()

    page.get_by_text("🔍 Compare CV versions").click()
    expect(page.get_by_text("Version A").first).to_be_visible()
    # Default selection compares the two newest versions -> a diff renders
    expect(page.get_by_text("@@", exact=False).first).to_be_visible()


def test_next_round_prep_requires_provider(page, app_url):
    _open_tracker(page, app_url)
    page.get_by_text("Add an application manually").click()
    fill_input(page, "Company", "PrepCo")
    fill_input(page, "Job title", "Interviewee")
    page.get_by_role("button", name="Add to tracker").click()

    page.get_by_text("Details, timeline & CV version used").first.click()
    expect(page.get_by_role("button", name="🎤 Prep me for the next round").first).to_be_visible()
    page.get_by_role("button", name="🎤 Prep me for the next round").first.click()
    expect(page.get_by_text("Configure an AI provider first", exact=False).first).to_be_visible()


def test_bulk_list_is_paginated(page, bulk_app_url):
    """With 200 applications the list paginates instead of rendering everything."""
    _open_tracker(page, bulk_app_url)
    expect(page.get_by_text("Applications", exact=True)).to_be_visible()

    # Only one page of cards is rendered at a time
    expect(page.get_by_text("Showing 1–10 of 200 applications")).to_be_visible()
    expect(page.get_by_text("Page 1 of 20").first).to_be_visible()

    page.get_by_role("button", name="Next ➡️").click()
    expect(page.get_by_text("Showing 11–20 of 200 applications")).to_be_visible()


def test_bulk_search_filters_list(page, bulk_app_url):
    _open_tracker(page, bulk_app_url)
    field = page.get_by_placeholder("Search company or job title...")
    field.fill("Company 042")
    field.press("Tab")
    expect(page.get_by_text("Showing 1–1 of 1 applications")).to_be_visible()
    expect(page.get_by_text("Company 042", exact=False).first).to_be_visible()


def test_bulk_board_caps_columns(page, bulk_app_url):
    """Board columns cap cards with a 'show all' rather than rendering hundreds."""
    _open_tracker(page, bulk_app_url)
    page.get_by_text("🗂️ Board").click()
    # 200 apps spread across 5 statuses -> 40 per column, capped at 20 with a show-all button
    expect(page.get_by_role("button", name="Show all 40").first).to_be_visible()
