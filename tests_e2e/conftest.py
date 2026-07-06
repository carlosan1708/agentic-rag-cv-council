"""End-to-end test fixtures: launch the Streamlit app and drive it with Playwright.

Run with:  python -m pytest tests_e2e
(The regular unit suite in tests/ does not include these.)
"""

import http.server
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
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


class _FakeOllamaHandler(http.server.BaseHTTPRequestHandler):
    """Minimal Ollama /api/tags endpoint so the real wizard flow works in tests."""

    def do_GET(self):
        if self.path == "/api/tags":
            body = json.dumps({"models": [{"name": "llama3.1:8b"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


def _start_fake_ollama() -> str:
    server = http.server.HTTPServer(("localhost", 0), _FakeOllamaHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://localhost:{server.server_port}"


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
    """The app in default (open) mode, with a stub Ollama server for the real wizard flow."""
    process, url = _launch_app(
        tmp_path_factory.mktemp("open-data"),
        {"AUTH_MODE": "open", "OLLAMA_BASE_URL": _start_fake_ollama()},
    )
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


SAMPLE_CV = """Alex Rivera
alex@example.com | +1 555 010 1234 | linkedin.com/in/alexrivera

Professional Summary
Backend engineer with six years of Python experience.

Work Experience
Software Engineer, Datawheel Labs (2021 - Present)
- Built APIs in Python on Kubernetes

Education
BSc Computer Science

Skills
Python, PostgreSQL, Docker, Kubernetes
"""

SAMPLE_JOB = "We need a Senior Python Engineer with Kubernetes, Docker and PostgreSQL experience."


def goto_team_via_wizard(page, url):
    """Shared helper: walk the REAL wizard (Ollama provider, CV upload, job text) to the team step."""
    page.goto(url)
    page.get_by_role("button", name="Get Started ➡️").click()
    page.get_by_text("Step 1: System Configuration").wait_for()
    page.get_by_text("Ollama", exact=True).click()
    page.get_by_text("Connected to local Ollama server!").wait_for()
    page.get_by_role("button", name="Next: Upload CV ➡️").click()
    page.get_by_text("Step 2: Upload Your CV").wait_for()

    with tempfile.TemporaryDirectory() as tmp_dir:
        cv_path = os.path.join(tmp_dir, "my_cv.txt")
        with open(cv_path, "w") as f:
            f.write(SAMPLE_CV)
        page.locator('input[type="file"]').set_input_files(cv_path)
        page.get_by_text("Successfully loaded", exact=False).wait_for()

    page.get_by_role("button", name="Next: Job Target ➡️").click()
    page.get_by_text("Step 3: Target Job Context").wait_for()
    job_field = page.get_by_label("Job Description Text")
    job_field.fill(SAMPLE_JOB)
    job_field.press("Tab")
    page.get_by_role("button", name="Next: Assemble Board ➡️").click()
    page.get_by_text("Step 4: Assemble Your Board").wait_for()


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
