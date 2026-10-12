#!/usr/bin/env python3
"""Render a video composition to MP4: every frame is seek(t) + a screenshot, piped into ffmpeg.

  render.py <project> [--preset draft|final|app-preview] [--workers 4] [--from 3 --to 8] [--gif]

Presets:
  draft        1x capture, 30 fps, quick x264. For review.
  final        2x capture downscaled with lanczos (crisper text), composition fps, BT.709, crf 16.
  app-preview  App Store app preview: composition must be 886x1920 (portrait) or 1920x886, 15-30 s,
               <=30 fps, H.264 High 4.0 at ~11 Mbps, with a silent stereo AAC 256k track (Apple requires audio).
Output goes to <project>/out/<name>-<preset>.mp4.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402

PRESETS = {
    "draft": {"scale": 1.0, "fps": 30, "crf": 23, "x264": "veryfast", "img": "jpeg"},
    "final": {"scale": 2.0, "fps": None, "crf": 16, "x264": "slow", "img": "png"},
    "app-preview": {"scale": 2.0, "fps": 30, "crf": None, "x264": "slow", "img": "png"},
}


def encode_args(preset: str, pr: dict) -> list[str]:
    v = ["-c:v", "libx264", "-preset", pr["x264"], "-pix_fmt", "yuv420p",
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
    if preset == "app-preview":
        return v + ["-profile:v", "high", "-level", "4.0", "-crf", "14", "-maxrate", "12M", "-bufsize", "24M"]  # Apple: "target 10-12 Mbps"; mostly-still video lands lower (MP4 drops CBR filler)
    return v + ["-crf", str(pr["crf"])]


def render_segment(html: Path, out: Path, f0: int, f1: int, fps: float, preset: str) -> None:
    pr = PRESETS[preset]
    ff = common.need_ffmpeg()
    with common.composition(html, scale=pr["scale"]) as (page, info):
        W, H = info["width"], info["height"]
        cmd = [ff, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
               "-vf", f"scale={W}:{H}:flags=lanczos,format=yuv420p", *encode_args(preset, pr), "-r", str(fps), str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(f0, f1):
            common.seek(page, f / fps)
            shot = page.screenshot(type=pr["img"], **({"quality": 92} if pr["img"] == "jpeg" else {}))
            proc.stdin.write(shot)
            if (f - f0) % max(1, int(fps)) == 0:
                print(f"\r  frame {f - f0 + 1}/{f1 - f0}", end="", flush=True)
        proc.stdin.close()
        if proc.wait():
            sys.exit("ffmpeg failed")
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--preset", default="final", choices=PRESETS)
    ap.add_argument("--workers", type=int, default=1, help="parallel browsers (split by frame range)")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float)
    ap.add_argument("--out")
    ap.add_argument("--gif", action="store_true", help="also write a GIF (720px wide, 15 fps)")
    ap.add_argument("--segment", nargs=3, metavar=("F0", "F1", "OUT"), help=argparse.SUPPRESS)
    a = ap.parse_args()
    html = common.project_html(a.project)
    ff = common.need_ffmpeg()

    with common.composition(html) as (_, info):
        pass
    if info["kind"] != "video":
        sys.exit("this project is boards (stills): use export.py")
    pr = PRESETS[a.preset]
    fps = float(min(pr["fps"] or info["fps"], 30 if a.preset == "app-preview" else 120))

    if a.segment:
        render_segment(html, Path(a.segment[2]), int(a.segment[0]), int(a.segment[1]), fps, a.preset)
        return

    if a.preset == "app-preview":
        if (info["width"], info["height"]) not in {(886, 1920), (1920, 886)}:
            sys.exit(f"app previews must be 886x1920 or 1920x886; this composition is {info['width']}x{info['height']} "
                     "(new.py --preset app-preview makes the right size)")
        if not 15 <= info["duration"] <= 30:
            sys.exit(f"app previews must be 15-30 s; this one is {info['duration']:.1f} s")

    t1 = min(a.t1 if a.t1 is not None else info["duration"], info["duration"])
    f0, f1 = round(a.t0 * fps), round(t1 * fps)
    proj = html.parent
    (proj / "out").mkdir(exist_ok=True)
    out = Path(a.out) if a.out else proj / "out" / f"{proj.name}-{a.preset}.mp4"
    print(f"{info['width']}x{info['height']} · {(f1 - f0) / fps:.1f} s · {fps:g} fps · preset {a.preset} · {a.workers} worker(s)")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        video_only = tmp / "video.mp4"
        if a.workers <= 1:
            render_segment(html, video_only, f0, f1, fps, a.preset)
        else:
            n = f1 - f0
            bounds = [f0 + n * i // a.workers for i in range(a.workers + 1)]
            segs = [tmp / f"seg{i}.mp4" for i in range(a.workers)]
            procs = [subprocess.Popen([sys.executable, __file__, str(html), "--preset", a.preset,
                                       "--segment", str(bounds[i]), str(bounds[i + 1]), str(segs[i])])
                     for i in range(a.workers)]
            if any(p.wait() for p in procs):
                sys.exit("a worker failed")
            (tmp / "list.txt").write_text("".join(f"file '{s}'\n" for s in segs))
            common.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-c", "copy", str(video_only)])

        if a.preset == "app-preview":
            common.run([ff, "-y", "-loglevel", "error", "-i", str(video_only), "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(out)])
        else:
            common.run([ff, "-y", "-loglevel", "error", "-i", str(video_only), "-c", "copy", "-movflags", "+faststart", str(out)])

    print(f"wrote {out}")
    if a.gif:
        gif = out.with_suffix(".gif")
        common.run([ff, "-y", "-loglevel", "error", "-i", str(out), "-vf",
                    "fps=15,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a", str(gif)])
        print(f"wrote {gif}")


if __name__ == "__main__":
    main()
