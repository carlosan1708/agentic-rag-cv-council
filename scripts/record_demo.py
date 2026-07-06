"""Records animated GIFs of the app for the README by driving the real UI.

Launches the Streamlit app, walks through the demo flow with Playwright,
captures frames, and assembles them into GIFs under docs/assets/.

Usage:  python scripts/record_demo.py
"""

import http.server
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import requests
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
VIEWPORT = {"width": 1100, "height": 900}
GIF_WIDTH = 880
FRAME_MS = 1600

CHROMIUM = "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


class _FakeOllamaHandler(http.server.BaseHTTPRequestHandler):
    """Minimal Ollama /api/tags endpoint so the provider step works on camera."""

    def do_GET(self):
        if self.path == "/api/tags":
            body = json.dumps({"models": [{"name": "llama3.1:8b"}, {"name": "mistral:7b"}]}).encode()
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


def _launch_app(port: int, tmp_dir: str, extra_env: dict = None) -> subprocess.Popen:
    env = os.environ.copy()
    env.update({"DATA_DIR": tmp_dir, "AUTH_MODE": "open", "ONLINE_MODE": "false"})
    env.update(extra_env or {})
    env.pop("GCS_BUCKET", None)
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "src/app.py", "--server.port", str(port), "--server.headless", "true"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(120):
        try:
            if requests.get(f"http://localhost:{port}/_stcore/health", timeout=1).ok:
                return process
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError("App did not start")


def _save_gif(frames: list, path: Path, frame_ms: int = FRAME_MS) -> None:
    images = []
    for png_bytes in frames:
        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        ratio = GIF_WIDTH / image.width
        image = image.resize((GIF_WIDTH, int(image.height * ratio)), Image.LANCZOS)
        images.append(image.quantize(colors=128, dither=Image.FLOYDSTEINBERG))

    durations = [frame_ms] * len(images)
    durations[0] = int(frame_ms * 1.5)  # linger on the first frame
    durations[-1] = int(frame_ms * 2)  # and the last

    images[0].save(path, save_all=True, append_images=images[1:], duration=durations, loop=0, optimize=True)
    print(f"wrote {path} ({path.stat().st_size // 1024} KB, {len(images)} frames)")


def _shot(page, frames: list, screenshots: dict = None, name: str = None, settle: float = 0.8):
    time.sleep(settle)
    png = page.screenshot()
    frames.append(png)
    if screenshots is not None and name:
        (ASSETS / f"{name}.png").write_bytes(png)


def record(url: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        page.set_default_timeout(30_000)

        # ---- Main demo flow GIF ----
        frames = []
        page.goto(url)
        page.get_by_text("Elevate Your Career with AI").wait_for()
        _shot(page, frames, {}, "welcome", settle=1.5)

        page.get_by_role("button", name="🎮 Try the Demo").click()
        page.get_by_text("Step 4: Assemble Your Board").wait_for()
        _shot(page, frames, {}, "team")

        page.get_by_role("button", name="Next: Run Analysis ➡️").click()
        page.get_by_text("Analysis Summary").wait_for()
        page.get_by_text("Also generate a tailored cover letter").click()
        _shot(page, frames, {}, "pre_run")

        page.get_by_role("button", name="🚀 Start Board Review").click()
        page.get_by_text("Analysis Complete!").first.wait_for()
        _shot(page, frames, {}, "results_board", settle=1.2)

        page.get_by_role("tab", name="🛠️ Minimal Changes").click()
        _shot(page, frames, {}, "results_changes")

        page.get_by_role("tab", name="📊 ATS Score").click()
        _shot(page, frames, {}, "results_ats")

        page.get_by_role("tab", name="📄 Final CV").click()
        _shot(page, frames, {}, "results_cv")

        page.get_by_role("tab", name="✉️ Cover Letter").click()
        _shot(page, frames, {}, "results_cover")

        page.get_by_role("tab", name="🎤 Interview Prep").click()
        page.get_by_role("button", name="🎤 Generate Interview Prep").click()
        page.get_by_text("Suggested Answers (STAR)").first.wait_for()
        _shot(page, frames, {}, "results_interview")

        _save_gif(frames, ASSETS / "demo.gif")

        # ---- ATS dashboard close-up GIF ----
        ats_frames = []
        page.get_by_role("tab", name="📊 ATS Score").click()
        _shot(page, ats_frames)
        page.get_by_role("tab", name="🛠️ Minimal Changes").click()
        _shot(page, ats_frames)
        page.get_by_role("tab", name="📊 ATS Score").click()
        _shot(page, ats_frames)
        _save_gif(ats_frames, ASSETS / "ats_score.gif", frame_ms=2000)

        browser.close()


def record_wizard(page, url: str) -> None:
    """Records the real (non-demo) wizard: setup -> upload -> job -> team -> ready to run.

    Uses the Ollama provider against a local stub so the model step works without
    a paid API key; the flow shown is exactly what users go through.
    """
    sys.path.insert(0, str(ROOT / "src"))
    from demo_data import DEMO_CV, DEMO_JOB  # sample content for the recording

    frames = []
    page.goto(url)
    page.get_by_text("Elevate Your Career with AI").wait_for()
    _shot(page, frames, {}, "wizard_welcome", settle=1.2)

    # Step 1: Setup - pick the local provider, models load for real
    page.get_by_role("button", name="Get Started ➡️").click()
    page.get_by_text("Step 1: System Configuration").wait_for()
    page.get_by_text("Ollama", exact=True).click()
    page.get_by_text("Connected to local Ollama server!").wait_for()
    _shot(page, frames, {}, "wizard_setup")

    # Step 2: Upload a CV file
    page.get_by_role("button", name="Next: Upload CV ➡️").click()
    page.get_by_text("Step 2: Upload Your CV").wait_for()
    with tempfile.TemporaryDirectory() as cv_dir:
        cv_path = os.path.join(cv_dir, "my_cv.txt")
        with open(cv_path, "w") as f:
            f.write(DEMO_CV)
        page.locator('input[type="file"]').set_input_files(cv_path)
        page.get_by_text("Successfully loaded", exact=False).wait_for()
        _shot(page, frames, {}, "wizard_upload")

    # Step 3: Paste the target job description
    page.get_by_role("button", name="Next: Job Target ➡️").click()
    page.get_by_text("Step 3: Target Job Context").wait_for()
    job_field = page.get_by_label("Job Description Text")
    job_field.fill(DEMO_JOB)
    job_field.press("Tab")
    page.get_by_role("button", name="Next: Assemble Board ➡️").click()

    # Step 4: Assemble the board
    page.get_by_text("Step 4: Assemble Your Board").wait_for()
    page.get_by_text("Cultural Fit Consultant (matchmaker)").click()
    _shot(page, frames, {}, "wizard_team")

    # Step 5: Ready to run
    page.get_by_role("button", name="Next: Run Analysis ➡️").click()
    page.get_by_text("Analysis Summary").wait_for()
    _shot(page, frames, {}, "wizard_ready", settle=1.0)

    _save_gif(frames, ASSETS / "wizard.gif", frame_ms=1800)


def _seed_tracker(tmp_dir: str) -> None:
    """Seeds a few applications so the tracker dashboard has data on camera."""
    os.environ["DATA_DIR"] = tmp_dir
    sys.path.insert(0, str(ROOT / "src"))
    from demo_data import DEMO_COVER_LETTER, DEMO_FINAL_CV
    from services.tracker_service import TrackerService

    entries = [
        ("Nimbus Analytics", "Senior Backend Engineer", "Interviewing", 92),
        ("Acme Corp", "Platform Engineer", "Applied", 78),
        ("Brightcart", "Staff Engineer", "Offer", 88),
        ("Initech", "Backend Developer", "Rejected", 64),
        ("Globex", "Python Engineer", "Applied", 71),
    ]
    ids = []
    for company, title, status, score in entries:
        ids.append(
            TrackerService.add_application(
                company=company,
                job_title=title,
                status=status,
                ats_score=score,
                job_description=f"Job Title: {title}\nCompany: {company}\nBackend role with Python and Kubernetes.",
                cv_markdown=DEMO_FINAL_CV,
                cover_letter=DEMO_COVER_LETTER,
            )
        )
    # A timeline on the most recent application so the details view has content
    TrackerService.add_event(ids[-1], "Recruiter call", "Intro call with Sam - team of 8, hybrid, hiring for Q3.")
    TrackerService.add_event(
        ids[-1], "Interview", "System design round: rate limiting + K8s autoscaling. Went well, follow-up Tuesday."
    )
    TrackerService.add_event(ids[-1], "Feedback", "Recruiter: positive signal from the panel, final round next week.")


def record_tracker(page, url: str) -> None:
    """Records the Job Tracker dashboard (full version): KPIs, pipeline, CV versions."""
    frames = []
    page.goto(url)
    page.get_by_text("Elevate Your Career with AI").wait_for()
    page.get_by_role("button", name="📋 Job Tracker - your applications & CV versions").click()
    page.get_by_text("Pipeline").wait_for()
    _shot(page, frames, {}, "tracker_dashboard", settle=1.2)

    page.get_by_text("Details, timeline & CV version used").first.click()
    page.get_by_role("button", name="📥 CV PDF").first.wait_for()
    page.get_by_text("Activity timeline").first.wait_for()
    time.sleep(0.8)
    page.mouse.wheel(0, 1100)
    _shot(page, frames, {}, "tracker_details", settle=0.8)

    page.get_by_text("Add an application manually").click()
    _shot(page, frames, {}, "tracker_add", settle=0.8)

    _save_gif(frames, ASSETS / "tracker.gif", frame_ms=2200)


def main():
    ollama_url = _start_fake_ollama()
    port = _free_port()
    with tempfile.TemporaryDirectory() as tmp_dir:
        _seed_tracker(tmp_dir)
        process = _launch_app(port, tmp_dir, extra_env={"OLLAMA_BASE_URL": ollama_url})
        try:
            record(f"http://localhost:{port}")
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()
                page = browser.new_page(viewport=VIEWPORT)
                page.set_default_timeout(30_000)
                record_wizard(page, f"http://localhost:{port}")
                record_tracker(page, f"http://localhost:{port}")
                browser.close()
        finally:
            process.terminate()


if __name__ == "__main__":
    main()
