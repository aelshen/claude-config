#!/usr/bin/env python3
"""Look at a composition without watching it: stills at chosen moments, contact sheets, and the lint.

  stills.py <project>                 settled still of every scene (or every board) + its checks, linted
  stills.py <project> --at 3.2 7.9    exact moments (taps, transitions)
  stills.py <project> --grid 24       contact sheet of 24 evenly spaced frames
  stills.py <file.mp4> --grid 24      contact sheet from a rendered video (what actually shipped)

PNGs go to <project>/out/stills/. Open and look at every one. Exits 1 if the lint found errors.
"""
import argparse
import math
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def sheet(frames: list[tuple[str, Image.Image]], out: Path, cols: int | None = None) -> None:
    cols = cols or min(6, max(2, round(math.sqrt(len(frames) * 1.6))))
    w = 360
    h = round(w * frames[0][1].height / frames[0][1].width)
    rows = math.ceil(len(frames) / cols)
    img = Image.new("RGB", (cols * (w + 8) + 8, rows * (h + 34) + 8), "#202020")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(common.SKILL / "fonts" / "Inter.ttf"), 18)
    for i, (label, f) in enumerate(frames):
        x, y = 8 + (i % cols) * (w + 8), 8 + (i // cols) * (h + 34)
        img.paste(f.convert("RGB").resize((w, h), Image.LANCZOS), (x, y))
        d.text((x, y + h + 6), label, fill="#dddddd", font=font)
    img.save(out)


def from_video(mp4: Path, n: int) -> None:
    ff = common.need_ffmpeg()
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                               capture_output=True, text=True).stdout.strip())
    out = mp4.parent / "stills"
    out.mkdir(exist_ok=True)
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            t = dur * (i + 0.5) / n
            p = Path(tmp) / f"{i}.png"
            common.run([ff, "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(mp4), "-frames:v", "1", str(p)])
            frames.append((f"{t:.2f}s", Image.open(p).copy()))
    target = out / f"{mp4.stem}-grid.png"
    sheet(frames, target)
    print(f"wrote {target}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--at", type=float, nargs="+", help="moments in seconds (whole-video time)")
    ap.add_argument("--grid", type=int, help="contact sheet of N frames")
    ap.add_argument("--scale", type=float, default=1.0)
    a = ap.parse_args()

    if a.project.endswith((".mp4", ".mov", ".m4v")):
        from_video(Path(a.project).expanduser().resolve(), a.grid or 24)
        return

    html = common.project_html(a.project)
    out = html.parent / "out" / "stills"
    out.mkdir(parents=True, exist_ok=True)
    errors = 0
    with common.composition(html, scale=a.scale) as (page, info):
        if info["kind"] == "boards":
            frames = []
            for b in info["boards"]:
                common.show(page, b)
                p = out / f"board-{b}.png"
                page.screenshot(path=str(p))
                errors += common.print_issues(common.lint(page), b)
                frames.append((b, Image.open(p).copy()))
                print(f"wrote {p}")
            if len(frames) > 1:
                sheet(frames, out / "boards.png", cols=len(frames))
                print(f"wrote {out / 'boards.png'}")
        else:
            moments: list[tuple[str, float]] = []
            if a.grid:
                moments = [(f"{info['duration'] * (i + 0.5) / a.grid:.2f}s", info["duration"] * (i + 0.5) / a.grid) for i in range(a.grid)]
            elif a.at:
                moments = [(f"{t:.2f}s", t) for t in a.at]
            else:
                for s in info["scenes"]:
                    moments.append((s["id"], s["start"] + max(s["duration"] - 0.45, s["duration"] * 0.75)))
                    moments += [(f"{s['id']}@{c:g}", s["start"] + c) for c in s["checks"]]
            frames = []
            for label, t in moments:
                common.seek(page, t)
                safe = label.replace("@", "-at-").replace("/", "-")
                p = out / f"{safe}.png"
                page.screenshot(path=str(p))
                errors += common.print_issues(common.lint(page), label)
                frames.append((label, Image.open(p).copy()))
                if not a.grid:
                    print(f"wrote {p}")
            if a.grid:
                sheet(frames, out / "grid.png")
                print(f"wrote {out / 'grid.png'}")
    print(f"lint: {errors} error(s)" if errors else "lint: no errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
