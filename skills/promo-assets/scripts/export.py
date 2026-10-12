#!/usr/bin/env python3
"""Export a boards project as final images at exact pixel sizes (App Store screenshots, link-preview cards).

  export.py <project>                        every board, PNG, at the composition's size
  export.py <project> --boards hook decks    only these
  export.py <project> --jpg                  JPEG instead (smaller; App Store accepts both)

Images are flattened to RGB (the App Store rejects alpha). Output: <project>/out/export/<board>.png.
The lint runs on each board; errors stop the export unless --force.
"""
import argparse
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402
from PIL import Image  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--boards", nargs="+")
    ap.add_argument("--jpg", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    html = common.project_html(a.project)
    out = html.parent / "out" / "export"
    out.mkdir(parents=True, exist_ok=True)
    with common.composition(html) as (page, info):
        if info["kind"] != "boards":
            sys.exit("this project is a video: use render.py (or stills.py --at for a poster frame)")
        ids = a.boards or info["boards"]
        for i, b in enumerate(ids, 1):
            if b not in info["boards"]:
                sys.exit(f"no board {b!r}; have {info['boards']}")
            common.show(page, b)
            errors = common.print_issues(common.lint(page), b)
            if errors and not a.force:
                sys.exit(f"lint errors on {b}: fix them, or --force")
            img = Image.open(io.BytesIO(page.screenshot(type="png"))).convert("RGB")
            assert img.size == (info["width"], info["height"]), img.size
            p = out / f"{i:02d}-{b}.{'jpg' if a.jpg else 'png'}"
            img.save(p, quality=95) if a.jpg else img.save(p, optimize=True)
            print(f"wrote {p}  {img.width}x{img.height}")


if __name__ == "__main__":
    main()
