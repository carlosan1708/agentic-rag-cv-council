"""E2E: demo mode is a teaser - full-version features are visibly locked."""

from conftest import start_demo
from playwright.sync_api import expect


def test_demo_board_is_fixed(page, app_url):
    start_demo(page, app_url)
    expect(page.get_by_text("Demo board is fixed", exact=False)).to_be_visible()
    # Persona checkboxes are disabled and the builder/debate are locked
    expect(page.get_by_role("checkbox").first).to_be_disabled()
    expect(page.get_by_text("Persona Builder: Add a Custom Specialist")).not_to_be_visible()
    expect(page.get_by_text("available in the full version", exact=False).first).to_be_visible()


def test_demo_upload_step_is_read_only(page, app_url):
    start_demo(page, app_url)
    page.get_by_role("button", name="⬅️ Back").click()  # team -> job
    page.get_by_text("Step 3: Target Job Context").wait_for()
    page.get_by_role("button", name="⬅️ Back").click()  # job -> upload
    page.get_by_text("Step 2: Upload Your CV").wait_for()

    expect(page.get_by_text("Uploading your own CV", exact=False)).to_be_visible()
    expect(page.get_by_text("Sample CV used by the demo:")).to_be_visible()
    expect(page.locator('input[type="file"]')).not_to_be_attached()


def test_demo_job_step_is_read_only(page, app_url):
    start_demo(page, app_url)
    page.get_by_role("button", name="⬅️ Back").click()  # team -> job
    page.get_by_text("Step 3: Target Job Context").wait_for()

    expect(page.get_by_text("Job-posting URL extraction", exact=False)).to_be_visible()
    expect(page.get_by_text("Sample job posting used by the demo:")).to_be_visible()
    expect(page.get_by_role("button", name="Extract 🔍")).not_to_be_visible()


def test_exit_demo_returns_to_full_wizard(page, app_url):
    start_demo(page, app_url)
    page.get_by_role("button", name="⬅️ Back").click()  # team -> job
    page.get_by_text("Step 3: Target Job Context").wait_for()
    page.get_by_role("button", name="Exit demo").click()
    # Reset lands on the real Step 1 with provider selection
    expect(page.get_by_text("Step 1: System Configuration")).to_be_visible()
    expect(page.get_by_text("Ollama", exact=True).first).to_be_visible()
