"""E2E: approval-based access gate (AUTH_MODE=approval)."""

import re

from conftest import ADMIN_CODE, fill_input
from playwright.sync_api import expect


def test_gate_blocks_anonymous_visitors(page, auth_app_url):
    page.goto(auth_app_url)
    expect(page.get_by_text("Private Beta")).to_be_visible()
    expect(page.get_by_role("tab", name="🔓 Login")).to_be_visible()
    expect(page.get_by_role("tab", name="✉️ Request Access")).to_be_visible()
    # The wizard is NOT reachable
    expect(page.get_by_text("Get Started ➡️")).not_to_be_visible()


def test_gate_demo_bypass(page, auth_app_url):
    page.goto(auth_app_url)
    page.get_by_role("button", name="🎮 Try the Demo").click()
    expect(page.get_by_text("Step 4: Assemble Your Board")).to_be_visible()


def test_login_with_unknown_user_fails(page, auth_app_url):
    page.goto(auth_app_url)
    fill_input(page, "Email", "ghost@example.com")
    fill_input(page, "Access code", "badcode1")
    page.get_by_role("button", name="🔓 Login").click()
    expect(page.get_by_text("Invalid email or access code.")).to_be_visible()


def test_full_request_approve_login_flow(page, auth_app_url):
    email = "carla@example.com"

    # 1. Request access and capture the code shown once
    page.goto(auth_app_url)
    page.get_by_role("tab", name="✉️ Request Access").click()
    fill_input(page, "Your email", email)
    page.get_by_role("button", name="✉️ Request Access").click()
    expect(page.get_by_text("Request registered!")).to_be_visible()
    code_element = page.locator("code").first
    access_code = code_element.inner_text().strip()
    assert re.fullmatch(r"[0-9a-f]{8}", access_code)

    # 2. Login before approval -> pending message
    page.get_by_role("tab", name="🔓 Login").click()
    fill_input(page, "Email", email)
    fill_input(page, "Access code", access_code)
    page.get_by_role("button", name="🔓 Login").click()
    expect(page.get_by_text("still pending approval", exact=False)).to_be_visible()

    # 3. Admin approves
    page.get_by_role("tab", name="🛡️ Admin").click()
    fill_input(page, "Admin code", ADMIN_CODE)
    expect(page.get_by_text(email).first).to_be_visible()
    page.get_by_role("button", name="✅ Approve").click()
    expect(page.get_by_text("No pending requests.")).to_be_visible()

    # 4. Login now succeeds and the wizard is reachable
    page.get_by_role("tab", name="🔓 Login").click()
    fill_input(page, "Email", email)
    fill_input(page, "Access code", access_code)
    page.get_by_role("button", name="🔓 Login").click()
    expect(page.get_by_text("Elevate Your Career with AI")).to_be_visible()
    # The logged-in indicator lives in the (collapsed) sidebar
    expect(page.get_by_text(f"Logged in as {email}", exact=False)).to_be_attached()


def test_wrong_admin_code_rejected(page, auth_app_url):
    page.goto(auth_app_url)
    page.get_by_role("tab", name="🛡️ Admin").click()
    fill_input(page, "Admin code", "not-the-code")
    expect(page.get_by_text("Wrong admin code.")).to_be_visible()
