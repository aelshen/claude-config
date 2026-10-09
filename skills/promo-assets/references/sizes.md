# Sizes and specs

Checked against Apple's pages on 2026-10-09. Apple changes these; re-check before a submission:
- https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications
- https://developer.apple.com/help/app-store-connect/reference/app-information/app-preview-specifications

## App Store screenshots (iPhone, portrait)

| Preset | Size | Display |
|---|---|---|
| `app-store-6.9` | 1320 x 2868 (also accepted: 1290 x 2796, 1260 x 2736) | 6.9" (Pro Max / Plus) |
| `app-store-6.5` | 1284 x 2778 (also 1242 x 2688) | 6.5" |
| `app-store-6.3` | 1206 x 2622 (also 1179 x 2556) | 6.3" |

- **Required:** at least one screenshot for the 6.3" class ("iPhone with Dynamic Island, medium display").
  Making the 6.9" set too covers the largest phones; Apple scales a set down for smaller ones.
- Up to 10 per size. PNG or JPEG, **no alpha** (`export.py` flattens to RGB).
- Text must be readable at thumbnail size in search results: headline ≥ ~90 px at 1320 wide.
- Same boards for another size: make a second project with the other preset and copy `data.js` + `media/`.

## App Store app preview (video)

Preset `app-preview`: 886 x 1920 portrait (1920 x 886 landscape), for 6.5"-6.9" iPhones.
- 15-30 s. Max 30 fps. H.264 High Profile Level 4.0 (Apple's target bitrate 10-12 Mbps), or ProRes 422 HQ.
- **Stereo audio is required**: `render.py --preset app-preview` adds a silent AAC 256k 48 kHz track.
- .mov / .m4v / .mp4, up to 500 MB. Processing in App Store Connect can take up to 24 h.
- Bitrate: mostly still footage encodes well below 10 Mbps, because MP4 drops x264's padding. Apple calls
  10-12 Mbps a target. If App Store Connect ever rejects one for bitrate, encode ProRes 422 HQ
  (`-c:v prores_ks -profile:v 3`, .mov).
- Apple's content rules: footage should be captured from the app itself (screen captures, not mockups of
  features that don't exist); keep text overlays short.

## Video presets

| Preset | Size | Use |
|---|---|---|
| `video` | 1920 x 1080 | site, YouTube, decks |
| `vertical` | 1080 x 1920 | Reels, Shorts, TikTok, Stories |
| `square` | 1080 x 1080 | feeds |

## Link-preview card

Preset `card`: 1200 x 630 (Open Graph / X / LinkedIn / iMessage previews). Keep the headline in the left
55%: some apps crop to a square from the center.
