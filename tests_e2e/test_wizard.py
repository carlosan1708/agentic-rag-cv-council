"""E2E: welcome screen and wizard navigation."""

from conftest import fill_input, start_demo
from playwright.sync_api import expect


def test_welcome_renders(page, app_url):
    page.goto(app_url)
    expect(page.get_by_text("AI - CV Advisory Board").first).to_be_visible()
    expect(page.get_by_text("Elevate Your Career with AI")).to_be_visible()
    expect(page.get_by_role("button", name="Get Started ➡️")).to_be_visible()
    expect(page.get_by_role("button", name="🎮 Try the Demo")).to_be_visible()


def test_get_started_shows_config_step(page, app_url):
    page.goto(app_url)
    page.get_by_role("button", name="Get Started ➡️").click()
    expect(page.get_by_text("Step 1: System Configuration")).to_be_visible()
    # All four providers offered
    for provider in ("Google", "OpenAI", "Anthropic", "Ollama"):
        expect(page.get_by_text(provider, exact=True).first).to_be_visible()


def test_stepper_visible_in_wizard(page, app_url):
    page.goto(app_url)
    page.get_by_role("button", name="Get Started ➡️").click()
    for label in ("Setup", "Upload", "Job", "Team", "Results"):
        expect(page.get_by_text(label).first).to_be_visible()


def test_config_next_disabled_without_models(page, app_url):
    page.goto(app_url)
    page.get_by_role("button", name="Get Started ➡️").click()
    expect(page.get_by_role("button", name="Next: Upload CV ➡️")).to_be_disabled()


def test_demo_jumps_to_team_step(page, app_url):
    start_demo(page, app_url)
    expect(page.get_by_text("Step 4: Assemble Your Board")).to_be_visible()
    # Personas from the packs are listed
    expect(page.get_by_text("LinkedIn Matchmaker").first).to_be_visible()
    expect(page.get_by_text("Technical Recruiter").first).to_be_visible()


def test_team_step_has_persona_builder_and_debate_toggle(page, app_url):
    start_demo(page, app_url)
    expect(page.get_by_text("Persona Builder: Add a Custom Specialist")).to_be_visible()
    expect(page.get_by_text("Debate round (Devil's Advocate)")).to_be_visible()


def test_custom_persona_can_be_added(page, app_url):
    start_demo(page, app_url)
    page.get_by_text("Persona Builder: Add a Custom Specialist").click()
    fill_input(page, "Specialist Name (e.g., 'Google Senior Engineer')", "E2E Reviewer")
    fill_input(page, "Backstory / focus", "You review CVs for e2e testing purposes.")
    page.get_by_role("button", name="Add to Board").click()
    expect(page.get_by_text("Your Custom Specialists")).to_be_visible()
    expect(page.get_by_text("E2E Reviewer").first).to_be_visible()
