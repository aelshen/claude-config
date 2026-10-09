#!/usr/bin/env python3
"""Screenshot the real product at phone size, to use as media in a composition ("show the product").

  capture.py http://localhost:8081/ --out media/library.png
  capture.py http://localhost:8081/word/x --out media/word.png --dark --wait-for "text=Meaning" --hide "#dev-banner"
  capture.py URL --out media/home.png --size 390x844 --scale 3       (defaults: an iPhone-sized 390x844 at 3x)

For an Expo app, run `npx expo start --web` and capture its pages. Logged-in or seeded state: use --storage
with a Playwright storage-state JSON, or --script with JS to run before the shot (e.g. open a sheet).
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="390x844")
    ap.add_argument("--scale", type=float, default=3)
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--wait-for", help="Playwright selector to wait for")
    ap.add_argument("--wait", type=int, default=800, help="extra ms to settle (fonts, images, animations)")
    ap.add_argument("--hide", nargs="*", default=[], help="selectors to hide")
    ap.add_argument("--script", help="JS to evaluate before the shot")
    ap.add_argument("--storage", help="Playwright storage-state JSON (cookies/localStorage)")
    a = ap.parse_args()
    w, h = map(int, a.size.lower().split("x"))
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=a.scale, is_mobile=True, has_touch=True,
                            color_scheme="dark" if a.dark else "light", storage_state=a.storage)
        page = ctx.new_page()
        page.goto(a.url, wait_until="networkidle")
        if a.wait_for:
            page.wait_for_selector(a.wait_for, timeout=20000)
        for sel in a.hide:
            page.add_style_tag(content=f"{sel} {{ visibility: hidden !important; }}")
        if a.script:
            page.evaluate(a.script)
        page.wait_for_timeout(a.wait)
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out))
        print(f"wrote {out}  {int(w * a.scale)}x{int(h * a.scale)}")
        b.close()


if __name__ == "__main__":
    main()
