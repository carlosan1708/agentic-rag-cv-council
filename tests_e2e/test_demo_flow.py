"""E2E: full demo analysis flow and the results dashboard."""

from conftest import run_demo_analysis
from playwright.sync_api import expect


def test_demo_run_shows_board_report(page, app_url):
    run_demo_analysis(page, app_url)
    expect(page.get_by_role("tab", name="📋 Board Report")).to_be_visible()
    expect(page.get_by_text("Executive Summary").first).to_be_visible()
    expect(page.get_by_text("demo mode", exact=False).first).to_be_visible()


def test_demo_results_have_all_tabs(page, app_url):
    run_demo_analysis(page, app_url)
    for tab in ("📋 Board Report", "🛠️ Minimal Changes", "📊 ATS Score", "📄 Final CV", "🎤 Interview Prep"):
        expect(page.get_by_role("tab", name=tab)).to_be_visible()


def test_minimal_changes_tab(page, app_url):
    run_demo_analysis(page, app_url)
    page.get_by_role("tab", name="🛠️ Minimal Changes").click()
    # Text unique to the optimizer output (also-similar text exists in the hidden report tab)
    expect(page.get_by_text("phrasing, not new experience").first).to_be_visible()


def test_ats_tab_shows_scores(page, app_url):
    run_demo_analysis(page, app_url)
    page.get_by_role("tab", name="📊 ATS Score").click()
    expect(page.get_by_text("ATS Match Score")).to_be_visible()
    expect(page.get_by_text("Original CV", exact=True)).to_be_visible()
    expect(page.get_by_text("Optimized CV", exact=True)).to_be_visible()
    expect(page.get_by_text("Keyword Coverage", exact=True)).to_be_visible()
    expect(page.get_by_text("Section checklist", exact=False).first).to_be_visible()


def test_final_cv_tab_downloads_docx_locked_in_demo(page, app_url):
    run_demo_analysis(page, app_url)
    page.get_by_role("tab", name="📄 Final CV").click()
    expect(page.get_by_role("button", name="📥 Download PDF")).to_be_visible()
    expect(page.get_by_role("button", name="🔒 DOCX export (full version)")).to_be_disabled()
    expect(page.get_by_text("Alex Rivera").first).to_be_visible()


def test_personalize_locked_in_demo(page, app_url):
    run_demo_analysis(page, app_url)
    expect(page.get_by_role("button", name="🔒 Personalize (full version)")).to_be_disabled()


def test_cover_letter_tab_when_requested(page, app_url):
    run_demo_analysis(page, app_url, cover_letter=True)
    page.get_by_role("tab", name="✉️ Cover Letter").click()
    expect(page.get_by_text("Dear Nimbus Analytics team,").first).to_be_visible()
    expect(page.get_by_role("button", name="📥 Download Cover Letter PDF")).to_be_visible()


def test_interview_prep_generates(page, app_url):
    run_demo_analysis(page, app_url)
    page.get_by_role("tab", name="🎤 Interview Prep").click()
    page.get_by_role("button", name="🎤 Generate Interview Prep").click()
    expect(page.get_by_text("Likely Interview Questions").first).to_be_visible()
    expect(page.get_by_text("Suggested Answers (STAR)").first).to_be_visible()


def test_history_appears_after_demo_run(page, app_url):
    run_demo_analysis(page, app_url)
    page.get_by_role("button", name="🏠 Start Over").click()
    # Reset returns to step 1; navigate back to the welcome screen state 0 via reload
    page.goto(app_url)
    expect(page.get_by_text("Previous Analyses", exact=False).first).to_be_visible()


def test_start_over_resets_wizard(page, app_url):
    run_demo_analysis(page, app_url)
    page.get_by_role("button", name="🏠 Start Over").click()
    expect(page.get_by_text("Step 1: System Configuration")).to_be_visible()
