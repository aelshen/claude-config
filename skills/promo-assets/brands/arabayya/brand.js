// arabayya brand for promo assets. Colors match sidequest.nexus `.t-arabayya` (styles.css) and the app's theme.
window.PROMO_BRAND = {
  id: "arabayya",
  name: "arabayya",
  tagline: "Read Arabic the way people speak it",
  url: "sidequest.nexus/arabayya",
  themes: {
    light: { bg: "#faf8f4", surface: "#ffffff", ink: "#1f2328", muted: "#646b77", line: "#e7e2d9", accent: "#0f766e", accentInk: "#ffffff", accentSoft: "#e0f0ed" },
    dark:  { bg: "#1c1b19", surface: "#242320", ink: "#ece9e2", muted: "#9aa1a8", line: "#454038", accent: "#2dd4bf", accentInk: "#0f2e2b", accentSoft: "#173a36" },
  },
  // Extra colors allowed by the lint (e.g. the app's word-type colors when shown in captures).
  extraColors: [],
  logos: {
    light: { wordmark: "logos/wordmark-light.svg", icon: "logos/icon-light.svg", stacked: "logos/stacked-light.svg" },
    dark:  { wordmark: "logos/wordmark-dark.svg",  icon: "logos/icon-dark.svg",  stacked: "logos/stacked-dark.svg" },
  },
  rtl: true, // shows Arabic: use lang="ar" on Arabic text so it gets the Arabic face and direction
};
