# Brands

A brand is a folder with a `brand.js`, plus its logos and, optionally, its own fonts:

```
<brand-id>/
  brand.js          window.PROMO_BRAND = {...}   (below)
  logos/*.svg       referenced from brand.js
  fonts/*.woff2     optional; referenced from brand.js
  PRIVATE           optional empty file: licensed fonts or non-public logos (see "Private brands")
```

## Where brands are found (first match wins)

1. `new.py --brands-dir <folder>`
2. `$PROMO_BRANDS`: colon-separated folders, e.g. `export PROMO_BRANDS=~/work-brands:~/clients/brands`
3. `~/.config/promo-assets/brands/`
4. `<skill-dir>/brands/`: the public brands that ship with the skill (Side Quest Nexus, arabayya, PlayPatch)

`new.py --list` shows every brand found and where it came from. A project remembers its brand folder in
`promo.json`, so `new.py <project> --update` refreshes from the same place.

## brand.js

```js
window.PROMO_BRAND = {
  id: "acme",                       // = folder name
  name: "Acme",                     // alt text for logos, default kicker
  tagline: "One line the end card uses",
  url: "acme.com",
  themes: {                         // every color the lint accepts as on-brand (plus extraColors, white, black)
    light: { bg, surface, ink, muted, line, accent, accentInk, accentSoft },   // hex strings
    dark:  { ...same keys },
  },
  extraColors: [],                  // other allowed colors (icon gradients, chart colors)
  logos: {                          // <img data-logo="wordmark|icon|stacked"> picks by theme
    light: { wordmark: "logos/wordmark-black.svg", icon: "logos/icon.svg" },
    dark:  { wordmark: "logos/wordmark-white.svg", icon: "logos/icon.svg" },
  },
  fonts: {                          // optional; default Inter + Noto Naskh Arabic (OFL, in the skill)
    sans:   { family: "Acme Sans", files: [{ src: "fonts/AcmeSans-Regular.woff2", weight: 400 },
                                           { src: "fonts/AcmeSans-Bold.woff2", weight: 700 }] },
    arabic: { family: "Acme Arabic", files: [{ src: "fonts/AcmeArabic.woff2", weight: 400 }] },
  },
  rtl: false,                       // true if the brand's assets show Arabic or Hebrew
};
```

Taking a brand from a website: its CSS variables are usually the colors (`:root` or a theme class); logos
are under its assets folder; the font is in its `@font-face` rules. Use the brand's official files, and don't
redraw a logo from type. If the organization has brand guidelines (a color palette, clear space around the
logo, rules on which color goes on which), follow them, and add the palette to `themes`/`extraColors` so the
lint enforces it.

## Private brands

A brand is private if it holds anything that isn't freely licensed or public: licensed fonts (most corporate
typefaces), unreleased logos, or a client's assets under NDA.

- **Never put a private brand in the skill's folder**: the skill is in a public repo. Use
  `~/.config/promo-assets/brands/` or a folder in that organization's own (private) repo, via `$PROMO_BRANDS`.
- Add an empty `PRIVATE` file to the brand folder. `new.py` then writes a `.gitignore` in each project that
  leaves out `brand/`, `fonts/` and `lib/`, and prints a reminder not to publish the folder.
- Share the rendered images and videos, not the project folder.
- Follow the organization's own rules for marketing: brand review, who approves external posts.
