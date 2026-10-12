---
name: promo-assets
description: Make promotional assets from code for any product or organization - App Store screenshots, App Store app preview videos, short demo/launch videos (16:9, 9:16, 1:1), and link-preview cards (Open Graph) - in that organization's brand (colors, logos, fonts), using real product captures. Each asset is one HTML page drawn deterministically, rendered with headless Chromium and ffmpeg, and checked through stills, contact sheets and a lint. Ships with Side Quest Nexus, arabayya and PlayPatch brands; other brands (including private ones with licensed fonts) load from outside the skill. Use when asked for App Store screenshots, an app preview, a promo/demo/teaser/launch video, a social clip, an OG image or link card, "marketing images", or to update any of these.
compatibility: macOS or Linux with Python 3.10+ and ffmpeg. One-time setup (scripts/setup.sh) builds a venv in the skill folder with Playwright, its Chromium, and Pillow. Rendering needs no network.
---

# Promo assets from code

Every asset is a web page. A **video** is one `index.html` whose `seek(t)` draws moment `t`; `render.py`
screenshots each frame and pipes them into ffmpeg. A **boards** project is one page with several fixed
images (App Store screenshots, a link card); `export.py` saves each at its exact pixel size. Because each
frame depends only on `t`, renders are identical every time and any edit is just a re-render.

You can't watch video, so check it the way an editor scrubs a timeline: **stills at chosen moments and
contact sheets**, then look at every PNG.

`<skill-dir>` is the folder holding this file (`~/.claude/skills/promo-assets`). Run every script with the
skill's own Python: `PY=<skill-dir>/.venv/bin/python`.

## Setup (once per machine)

Check first: `test -x <skill-dir>/.venv/bin/python && command -v ffmpeg` - if both pass, skip to Brands.

1. **ffmpeg** (encodes the videos and reads frames back for contact sheets):
   macOS `brew install ffmpeg`; Debian/Ubuntu `sudo apt install ffmpeg`. Needs `libx264` (both of those include it).
   Ask before installing system packages.
2. **The skill's venv**: `bash <skill-dir>/scripts/setup.sh`. It:
   - creates `<skill-dir>/.venv` with `python3 -m venv` (needs Python 3.10+; `python3 --version`);
   - installs `requirements.txt` (Playwright, Pillow) into it;
   - downloads Playwright's Chromium (~150 MB, into `~/Library/Caches/ms-playwright` on macOS,
     `~/.cache/ms-playwright` on Linux; shared by every Playwright install on the machine).
   Re-running is safe. On Linux, if Chromium fails to start: `<skill-dir>/.venv/bin/python -m playwright install-deps chromium`.
3. **Check it works**: `$PY <skill-dir>/scripts/new.py --list` lists brands and presets; a first
   `stills.py` run on a new project should end with `lint: no errors`.

What's not needed: Node, Xcode, a GPU, a network connection while rendering, or any font install (fonts
are in `<skill-dir>/fonts/` and inside each brand).

**Moving or renaming the skill folder breaks the venv** (venvs hold absolute paths): delete `.venv` and run
`setup.sh` again. The venv, `__pycache__` and every project's `out/` are gitignored.

Troubleshooting:
| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: playwright` | You used the system `python3`; use `$PY`, or run `setup.sh` |
| `Executable doesn't exist ... chromium` | `$PY -m playwright install chromium` |
| `ffmpeg not found` | Install it (step 1) |
| lint `font failed to load` / text looks like Times | A font path in `brand.js` is wrong, or a brand font file is missing |
| `page error: ...` | A JavaScript error in the project's `index.html`/`data.js`; open `index.html` in a browser and check the console |
| Render differs from the browser preview | Something isn't driven by `t` (a CSS transition, a timer); see Build rules |

| Read | When |
|---|---|
| `references/sizes.md` | Before making store assets: App Store screenshot and preview specs, link-card sizes |
| `references/craft.md` | Planning a story, timing, motion, copy, and the QA checklist |
| `references/brands.md` | Adding a brand, private brands (licensed fonts), where brands are looked up |
| `runtime/promo.js` header | The scene/board API and the `fx` motion helpers (rise, fade, pop, wipe, type, count, tap) |

## Brands

A brand is a folder with `brand.js` (light/dark colors, logos, name, tagline, url, optional fonts) - format in
`references/brands.md`. `new.py --list` shows what's available. Shipped (public): `sidequest`, `arabayya`,
`playpatch`, with colors from `sidequest.nexus/styles.css`.

Other organizations' brands live **outside this skill**: `~/.config/promo-assets/brands/<id>/`, or any folder
on `$PROMO_BRANDS`, or `--brands-dir`. **This skill is in a public repo: never add a brand with licensed fonts,
non-public logos or client material to `<skill-dir>/brands/`.** Mark such a brand with an empty `PRIVATE` file
so its projects gitignore the brand files. Don't have the brand? Ask for its logo files, colors and font (or its
website, and take the CSS variables and assets from there).

Default fonts are Inter and Noto Naskh Arabic (OFL, `fonts/`); a brand can bring its own.

## Workflow

### 1. Story first
Find out what's being promoted, the one thing a viewer should remember, where it goes (App Store, site,
social) and the proof (real screens, real numbers). For a video, write a storyboard table - scene, seconds,
headline, visual, data source - and show it. Default arc: hook (3-4 s) → 1-3 product beats (5-8 s) → proof
(4-6 s) → end card (3-4 s). For screenshots, one message per screenshot, the strongest first.

### 2. Scaffold
```bash
$PY <skill-dir>/scripts/new.py --list
$PY <skill-dir>/scripts/new.py promo/<name> --brand arabayya --preset app-store-6.9   # or app-preview, video, vertical, square, card
```
Put it where the project keeps things (e.g. `<repo>/promo/<name>/`; add `out/` to `.gitignore`), never inside
the skill folder. Add `--brands-dir <folder>` for a brand outside the default places.
`--update` later refreshes `lib/`, `brand/`, `fonts/` from the skill without touching `index.html`/`data.js`.

### 3. Real product, real numbers
Capture the real app instead of mocking it. For a flow (tap a word, a sheet opens, save it), write a small
`build_media.py` in the project that drives the app with Playwright in a fresh browser - skip onboarding and tips
the way a new user would, hide web-only hints the phone app doesn't show - and saves each state plus the
positions of what gets tapped (`media/layout.json`), so the video's taps land on the real buttons. Then
animate between states (scroll the text, slide the sheet up, push to the next screen) instead of cross-fading
stills. Quick single shots:
```bash
$PY <skill-dir>/scripts/capture.py http://localhost:8081/ --out promo/<name>/media/library.png
$PY <skill-dir>/scripts/capture.py http://localhost:8081/word/x --dark --wait-for "text=Meaning" --out ...
```
(390x844 at 3x by default; for Expo, `npx expo start --web`.) Copy and numbers live in `data.js`. A number
that comes from data (word counts, books) is computed by a small `build_data.py` that writes `data.js`, never
typed. Until the real thing exists, keep `SAMPLE: true` - it puts "Sample" on every frame - and say what to replace.

### 4. Build
Edit `data.js` first; edit `index.html` when the layout needs to change. Rules that keep renders reliable:
- Every visual is a function of `t`. No timers, `Date.now`, `Math.random`, CSS transitions or animations; use
  `Promo.random(seed)`.
- `render(t)` sets every animated property every call (`fx.*` do); build DOM in `setup`.
- Arabic text goes in an element with `lang="ar"` (gets Noto Naskh and RTL). `fx.type` is grapheme-safe.
- Surfaces: `s-bg`, `s-surface`, `s-accent`, `s-soft`, `s-ink`; text is ink/muted/accent on them.
  Phone: `<div class="phone"><img src="media/x.png"></div>` (add `.island` only if the shot has a status bar).
- Don't give elements ids that are browser globals (`screen`, `history`, `location`, `name`, `top`, `parent`):
  `id="x"` is reachable as `x` in scripts only when it doesn't shadow one.
- Don't put CSS `transform` on anything `render()` animates (`set()` replaces it); position with left/top/margin.
- Opt-outs for intentional cases: `data-bleed` (may leave the safe area), `data-overlap-ok`, `data-viz`
  (any colors, for charts), `data-lint-ignore`.

### 5. Look (stills + lint)
```bash
$PY <skill-dir>/scripts/stills.py promo/<name>               # each scene's settled frame (or each board) + lint
$PY <skill-dir>/scripts/stills.py promo/<name> --at 3.3 9.1  # exact moments: taps, transitions
$PY <skill-dir>/scripts/stills.py promo/<name> --grid 12     # contact sheet
```
**Open every PNG** in `out/stills/`. The lint catches mechanical problems - text cut off, outside the 4% safe
area, running into another text, image or the phone, too small for a phone, Arabic without the Arabic face,
off-brand colors, images or fonts that didn't load - and exits 1 on errors. It can't judge story, hierarchy,
spacing that is tight but not touching, or whether a tap lands on the right thing: your eyes on the stills do.

### 6. Render / export
```bash
$PY <skill-dir>/scripts/render.py promo/<name> --preset draft --workers 4      # quick review MP4
$PY <skill-dir>/scripts/render.py promo/<name> --workers 4                     # final (2x capture, crf 16)
$PY <skill-dir>/scripts/render.py promo/<name> --preset app-preview --workers 4  # App Store preview spec
$PY <skill-dir>/scripts/stills.py promo/<name>/out/<name>-final.mp4 --grid 12  # check what was encoded
$PY <skill-dir>/scripts/export.py promo/<name>                                 # boards → out/export/*.png (RGB, exact size)
```
A 20 s video takes about 25 s with 4 workers. Run renders in the foreground. `--gif` adds a GIF.

### 7. Deliver
Give the files plus: scene list with timings, where each number came from, how to edit (`data.js`, then
re-run), and what still needs a human - sample data to replace, Arabic copy for a native check, and the
owner's approval before anything is uploaded to the App Store or posted.

## Rules
- **Show the real product.** Captures of the app beat illustrations; no stock footage, glows or AI art.
- **User-facing copy follows the project's own rules** (arabayya: no linguistics jargon; Arabic checked by a
  native speaker before it ships).
- **One idea per frame.** A phone screenshot has room for a headline and one line.
- Never upload, post or submit anything yourself; hand the files to the owner.
- Follow the organization's own approval rules for anything external (brand review, legal, who signs off).
