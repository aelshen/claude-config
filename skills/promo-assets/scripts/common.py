"""Shared helpers: open a composition's index.html in headless Chromium and talk to window.__promo."""
import contextlib
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent


def need_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        sys.exit("ffmpeg not found: brew install ffmpeg")
    return exe


def project_html(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    html = p / "index.html" if p.is_dir() else p
    if not html.exists():
        sys.exit(f"no index.html at {p}")
    return html


@contextlib.contextmanager
def composition(html: Path, scale: float = 1.0):
    """Yields (page, info) with the page sized to the composition and fonts/images loaded."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--font-render-hinting=none", "--disable-lcd-text", "--force-color-profile=srgb"])
        # Read the size first at scale 1, then reopen at the real size and scale.
        page = browser.new_page()
        page.goto(html.as_uri() + "?render=1")
        info = wait_ready(page)
        page.close()
        page = browser.new_page(viewport={"width": info["width"], "height": info["height"]}, device_scale_factor=scale)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(html.as_uri() + "?render=1")
        info = wait_ready(page)
        if errors:
            sys.exit("page error: " + errors[0])
        try:
            yield page, info
        finally:
            browser.close()


def wait_ready(page) -> dict:
    from playwright.sync_api import Error
    try:
        page.wait_for_function("window.__promo !== undefined", timeout=15000)
        page.evaluate("() => window.__promo.ready")
    except Error as e:
        msg = str(e).split("\n")
        sys.exit("the composition failed to start: " + " | ".join(l.strip() for l in msg[:3]))
    return page.evaluate("""() => { const p = window.__promo;
        return { kind: p.kind, width: p.width, height: p.height, fps: p.fps, duration: p.duration,
                 scenes: p.scenes, boards: p.boards }; }""")


def seek(page, t: float) -> None:
    page.evaluate("t => window.__promo.seek(t)", t)


def show(page, board: str) -> None:
    page.evaluate("id => window.__promo.show(id)", board)


def lint(page) -> list[dict]:
    return page.evaluate("() => window.__promo.lint()")


def print_issues(issues: list[dict], when: str) -> int:
    """Prints issues; returns the number of errors."""
    seen = set()
    for i in issues:
        key = (i["level"], i["kind"], i["msg"])
        if key in seen:
            continue
        seen.add(key)
        print(f"  {i['level'].upper():5} {when:>10}  {i['kind']:9} {i['msg']}  [{i['where']}]")
    return sum(1 for i in issues if i["level"] == "error")


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{cmd[0]} failed:\n{r.stderr[-2000:]}")
