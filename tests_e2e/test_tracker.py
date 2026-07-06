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

    page.get_by_text("Details, notes & CV version used").first.click()
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
