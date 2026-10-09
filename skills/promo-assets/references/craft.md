# Craft: story, timing, motion, copy, QA

## Story
- One thing to remember. If the storyboard has two, make two assets.
- Lead with what the person gets ("Read Arabic the way people speak it"), not with features or tech.
- Proof is something real on screen: the app doing the thing, a real count, a real book.

## Timing
- Viewers need about 1 s per 3-4 words to read. A headline of 8 words needs ≥ 2.5 s settled on screen.
- Anything that animates in must finish ≥ 1.5 s before its scene ends, or the takeaway never gets read.
- A tap: show the marker ~0.25 s before the press, change the screen ~0.15 s after it (`fx.tap` + `fx.fade`).
- Count-ups: 1.2-1.8 s. Longer feels slow, shorter can't be read.
- App previews: put the strongest moment in the first 3 s; autoplay is muted and people scroll.

## Motion
- Entrances: `fx.rise` 0.6-0.8 s, `ease.out`, staggered 0.1-0.2 s. Exits short (0.3 s) or a cut.
- Springs (`fx.pop`, speed 9-14) only for small things: chips, badges, the logo.
- Scene changes: `enter: 'fade'` (0.4 s overlap) within one look; `'cut'` between very different surfaces.
- No CSS transitions or keyframes: they don't follow `seek(t)`.

## Copy
- Headlines: ≤ 6 words for screenshots, ≤ 8 for video. Sentence case. No period on headlines.
- Each project's own writing rules apply (arabayya: plain words, no grammar terms in headlines; Arabic only
  after a native check).
- Numbers come from data. "1,200 words" must be computed, not typed.

## QA checklist (look at the stills)
- [ ] Every scene's settled still: hierarchy obvious in one glance; nothing crowded against an edge.
- [ ] Taps (`--at`): the marker sits on the thing that changes.
- [ ] Arabic reads right to left, with vowel marks intact, and isn't clipped at the top or bottom.
- [ ] Dark and light themes both checked if both ship.
- [ ] The rendered file (`stills.py <mp4> --grid`) matches the previews: no blank or stuck frames.
- [ ] `SAMPLE` is off and "Sample" is gone before anything leaves the machine.
