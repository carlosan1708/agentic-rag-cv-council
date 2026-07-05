"""End-to-end test fixtures: launch the Streamlit app and drive it with Playwright.

Run with:  python -m pytest tests_e2e
(The regular unit suite in tests/ does not include these.)
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parent.parent

# Streamlit reruns the whole script per interaction and the first load imports
# CrewAI - give assertions generous room.
expect.set_options(timeout=20_000)

ADMIN_CODE = "e2e-admin-code"


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Use the pre-installed Chromium when available (e.g. sandboxed environments)."""
    prebuilt = "/opt/pw-browsers/chromium"
    if os.path.exists(prebuilt):
        return {**browser_type_launch_args, "executable_path": prebuilt}
    return browser_type_launch_args


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


def _launch_app(tmp_dir: Path, extra_env: dict) -> tuple:
    port = _free_port()
    env = os.environ.copy()
    env.update(
        {
            "DATA_DIR": str(tmp_dir),
            "ONLINE_MODE": "false",
            "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        }
    )
    env.pop("GCS_BUCKET", None)
    env.update(extra_env)

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/app.py",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(120):
        try:
            if requests.get(f"http://localhost:{port}/_stcore/health", timeout=1).ok:
                break
        except requests.RequestException:
            pass
        time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError("Streamlit app did not become healthy")

    return process, f"http://localhost:{port}"


@pytest.fixture(scope="session")
def app_url(tmp_path_factory):
    """The app in default (open) mode."""
    process, url = _launch_app(tmp_path_factory.mktemp("open-data"), {"AUTH_MODE": "open"})
    yield url
    process.terminate()


@pytest.fixture(scope="session")
def auth_app_url(tmp_path_factory):
    """The app in approval-gated mode with an admin code."""
    process, url = _launch_app(
        tmp_path_factory.mktemp("auth-data"),
        {"AUTH_MODE": "approval", "ADMIN_CODE": ADMIN_CODE},
    )
    yield url
    process.terminate()


@pytest.fixture(autouse=True)
def _default_timeout(page):
    page.set_default_timeout(20_000)


def fill_input(page, label, value, exact=True):
    """Fills a Streamlit input and blurs it so the value is committed before a click."""
    field = page.get_by_label(label, exact=exact)
    field.fill(value)
    field.press("Tab")


def start_demo(page, url):
    """Shared helper: open the app and enter demo mode from the welcome screen."""
    page.goto(url)
    page.get_by_role("button", name="🎮 Try the Demo").click()
    page.get_by_text("Assemble Your Board").wait_for()


def run_demo_analysis(page, url, cover_letter: bool = False):
    """Shared helper: demo mode → run the board → results tabs visible."""
    start_demo(page, url)
    page.get_by_role("button", name="Next: Run Analysis ➡️").click()
    page.get_by_text("Analysis Summary").wait_for()
    if cover_letter:
        page.get_by_text("Also generate a tailored cover letter").click()
    page.get_by_role("button", name="🚀 Start Board Review").click()
    page.get_by_text("Analysis Complete!").first.wait_for()
