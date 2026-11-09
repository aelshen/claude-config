// PlayPatch brand for promo assets: the Patchwork identity (apps/web tailwind.config.ts and
// docs/BRAND.md in the PlayPatch repo). Warm paper background, tomato accent, plum and teal patches.
// Fonts: Figtree (body) and Fraunces (headlines), both SIL OFL; Fraunces is exposed as --font-display.
window.PROMO_BRAND = {
  id: "playpatch",
  name: "PlayPatch",
  tagline: "Every video approved by a parent first",
  url: "playpatch.app",
  themes: {
    light: { bg: "#FBF6EC", surface: "#FFFFFF", ink: "#2B2420", muted: "#6E5E4F", line: "#E8DDCB", accent: "#C2410C", accentInk: "#FFFFFF", accentSoft: "#FCE2D5" },
    dark:  { bg: "#1C1714", surface: "#2B2420", ink: "#FBF7F0", muted: "#D6C7B0", line: "#54473C", accent: "#EB7650", accentInk: "#1C1714", accentSoft: "#3B312A" },
  },
  extraColors: ["#E4572E", "#6F4778", "#F0E3F0", "#2A9D8F", "#D6F0EB", "#F8C3AA", "#FBF7F0"],
  logos: {
    light: { icon: "logos/icon.svg" },
    dark:  { icon: "logos/icon.svg" },
  },
  fonts: {
    sans: { family: "Figtree", files: [{ src: "fonts/figtree-latin.woff2", weight: "300 900" }] },
    display: { family: "Fraunces", files: [{ src: "fonts/fraunces-latin.woff2", weight: "400 900" }] },
  },
  rtl: false,
};
