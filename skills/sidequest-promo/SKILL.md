---
name: sidequest-promo
description: Make promotional assets for Side Quest Nexus projects (arabayya, PlayPatch, the company site) from code - App Store screenshots, App Store app preview videos, short demo/launch videos (16:9, 9:16, 1:1), and link-preview cards - in each project's own brand, with real product captures. Each asset is one HTML page drawn deterministically and rendered with headless Chromium and ffmpeg, then checked through stills, contact sheets and a lint. Use when asked for screenshots for the App Store, an app preview, a promo/demo/teaser video, a social clip, an OG image or link card, "marketing images", or to update any of these, for any Side Quest project.
compatibility: Needs ffmpeg (brew install ffmpeg) and the skill's own venv (scripts/setup.sh installs Playwright + Chromium + Pillow into <skill-dir>/.venv).
---

# Side Quest promo assets

Every asset is a web page. A **video** is one `index.html` whose `seek(t)` draws moment `t`; `render.py`
screenshots each frame and pipes them into ffmpeg. A **boards** project is one page with several fixed
images (App Store screenshots, a link card); `export.py` saves each at its exact pixel size. Because each
frame depends only on `t`, renders are identical every time and any edit is just a re-render.

You can't watch video, so check it the way an editor scrubs a timeline: **stills at chosen moments and
contact sheets**, then look at every PNG.

`<skill-dir>` is the folder holding this file; run scripts with `<skill-dir>/.venv/bin/python`
(first time: `bash <skill-dir>/scripts/setup.sh`). Let `PY=<skill-dir>/.venv/bin/python`.

| Read | When |
|---|---|
| `references/sizes.md` | Before making store assets: App Store screenshot and preview specs, link-card sizes |
| `references/craft.md` | Planning a story, timing, motion, copy, and the QA checklist |
| `runtime/promo.js` header | The scene/board API and the `fx` motion helpers (rise, fade, pop, wipe, type, count, tap) |

## Brands

`brands/<id>/brand.js` per project: light/dark colors (copied from `sidequest.nexus/styles.css`), logos,
name, tagline, url. Present: `arabayya`, `playpatch`, `sidequest`. **Add a project** by copying a folder,
taking its colors from the website's `.t-<project>` block and its logos from `public/<project>/assets/`.
Fonts are Inter and Noto Naskh Arabic (both OFL, in `fonts/`), so projects can be shared and published.

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
Put it where the project keeps things (e.g. `<repo>/promo/<name>/`; add `out/` to `.gitignore`).
`--update` later refreshes `lib/`, `brand/`, `fonts/` from the skill without touching `index.html`/`data.js`.

### 3. Real product, real numbers
Capture the real app instead of mocking it:
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
