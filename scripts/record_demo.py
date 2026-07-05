"""Records animated GIFs of the app for the README by driving the real UI.

Launches the Streamlit app, walks through the demo flow with Playwright,
captures frames, and assembles them into GIFs under docs/assets/.

Usage:  python scripts/record_demo.py
"""

import io
import os
import socket
import subprocess
import sys
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


def _launch_app(port: int, tmp_dir: str) -> subprocess.Popen:
    env = os.environ.copy()
    env.update({"DATA_DIR": tmp_dir, "AUTH_MODE": "open", "ONLINE_MODE": "false"})
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


def main():
    import tempfile

    port = _free_port()
    with tempfile.TemporaryDirectory() as tmp_dir:
        process = _launch_app(port, tmp_dir)
        try:
            record(f"http://localhost:{port}")
        finally:
            process.terminate()


if __name__ == "__main__":
    main()
