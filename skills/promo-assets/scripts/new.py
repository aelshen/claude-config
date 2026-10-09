#!/usr/bin/env python3
"""Start a promo project for one brand.

  new.py <dir> --brand arabayya --preset app-store-6.9      App Store screenshots (boards)
  new.py <dir> --brand arabayya --preset app-preview        App Store app preview video, 886x1920
  new.py <dir> --brand playpatch --preset video             16:9 launch/demo video
  new.py <dir> --brand sidequest --preset card              1200x630 link-preview image
  new.py --list                                             brands and presets

The project is self-contained: index.html + data.js (edit these), lib/ (runtime), brand/ (colors, logos),
fonts/ (Inter and Noto Naskh Arabic, OFL), media/ (screenshots, captures), out/ (renders).
Re-run with --update to refresh lib/, brand/ and fonts/ from the skill without touching index.html or data.js.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent

PRESETS = {
    # name: (template, width, height, extra)
    "video": ("video", 1920, 1080, {"fps": 30}),
    "vertical": ("video", 1080, 1920, {"fps": 30}),
    "square": ("video", 1080, 1080, {"fps": 30}),
    "app-preview": ("video", 886, 1920, {"fps": 30, "app_preview": True}),
    "app-store-6.9": ("app-store", 1320, 2868, {}),
    "app-store-6.5": ("app-store", 1284, 2778, {}),
    "app-store-6.3": ("app-store", 1206, 2622, {}),
    "card": ("card", 1200, 630, {}),
}


def brand_dirs(extra: str | None = None) -> list[Path]:
    """Where brands are looked up, first match wins: --brands-dir, $PROMO_BRANDS (colon-separated),
    ~/.config/promo-assets/brands, then the brands that ship with the skill. Keep private brands (licensed fonts,
    client logos) in one of the first three, outside this skill's repo."""
    dirs = [extra] if extra else []
    dirs += [d for d in os.environ.get("PROMO_BRANDS", "").split(":") if d]
    dirs += [str(Path.home() / ".config" / "promo-assets" / "brands"), str(SKILL / "brands")]
    return [Path(d).expanduser().resolve() for d in dirs if Path(d).expanduser().is_dir()]


def brands(extra: str | None = None) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for d in brand_dirs(extra):
        for p in sorted(d.iterdir()):
            if (p / "brand.js").exists() and p.name not in found:
                found[p.name] = p
    return found


def refresh(dest: Path, brand_path: Path) -> None:
    for name, src in (("lib", SKILL / "runtime"), ("fonts", SKILL / "fonts"), ("brand", brand_path)):
        if (dest / name).exists():
            shutil.rmtree(dest / name)
        shutil.copytree(src, dest / name)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", nargs="?")
    ap.add_argument("--brand")
    ap.add_argument("--preset", default="video", choices=PRESETS)
    ap.add_argument("--theme", default="light", choices=["light", "dark"])
    ap.add_argument("--brands-dir", help="extra folder of brands (also: $PROMO_BRANDS, ~/.config/promo-assets/brands)")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list or not a.dir:
        print("brands:")
        for k, p in brands(a.brands_dir).items():
            print(f"  {k:14} {p}")
        print("presets:")
        for k, (tpl, w, h, _) in PRESETS.items():
            print(f"  {k:14} {tpl:9} {w}x{h}")
        return
    dest = Path(a.dir).expanduser().resolve()
    meta_path = dest / "promo.json"
    if a.update:
        if not meta_path.exists():
            sys.exit(f"{dest} isn't a promo project (no promo.json)")
        meta = json.loads(meta_path.read_text())
        name = a.brand or meta["brand"]
        found = brands(a.brands_dir or meta.get("brands_dir"))
        if name not in found:
            sys.exit(f"brand {name!r} not found in {[str(d) for d in brand_dirs(a.brands_dir)]}")
        refresh(dest, found[name])
        print(f"refreshed lib/, brand/, fonts/ in {dest}")
        return
    found = brands(a.brands_dir)
    if not a.brand or a.brand not in found:
        sys.exit(f"--brand is one of: {', '.join(found)} (searched {', '.join(str(d) for d in brand_dirs(a.brands_dir))})")
    if (dest / "index.html").exists():
        sys.exit(f"{dest} already has an index.html")
    tpl, w, h, extra = PRESETS[a.preset]
    dest.mkdir(parents=True, exist_ok=True)
    for f in (SKILL / "templates" / tpl).iterdir():
        (shutil.copytree if f.is_dir() else shutil.copy)(f, dest / f.name)
    refresh(dest, found[a.brand])
    (dest / "media").mkdir(exist_ok=True)
    data = (dest / "data.js").read_text()
    size = {"width": w, "height": h, "theme": a.theme, **extra}
    data = data.replace("/*SIZE*/", json.dumps(size))
    (dest / "data.js").write_text(data)
    meta_path.write_text(json.dumps({"brand": a.brand, "brands_dir": str(found[a.brand].parent), "preset": a.preset, **size}, indent=1) + "\n")
    if (found[a.brand] / "PRIVATE").exists():
        (dest / ".gitignore").write_text("out/\nbrand/\nfonts/\nlib/\n")
        print(f"  note: brand {a.brand!r} is private (licensed fonts or logos): brand/ is gitignored here; don't publish this folder")
    print(f"new {tpl} project for {a.brand} at {dest} ({w}x{h}, {a.theme})")
    print(f"  edit data.js and index.html; preview: open {dest / 'index.html'}")
    print(f"  look:   {SKILL}/.venv/bin/python {SKILL}/scripts/stills.py {dest}")
    if tpl == "video":
        print(f"  render: {SKILL}/.venv/bin/python {SKILL}/scripts/render.py {dest} --preset {'app-preview' if a.preset == 'app-preview' else 'draft'}")
    else:
        print(f"  export: {SKILL}/.venv/bin/python {SKILL}/scripts/export.py {dest}")


if __name__ == "__main__":
    main()
