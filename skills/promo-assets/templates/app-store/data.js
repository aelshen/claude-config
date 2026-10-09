// App Store screenshots: one board per screenshot, in store order. Copy is short: a phone shows 2-3 lines.
// Replace SAMPLE shots with real captures (scripts/capture.py) and delete SAMPLE when they're real.
window.DATA = {
  size: /*SIZE*/,
  SAMPLE: true,
  boards: [
    // surface: s-bg | s-accent | s-soft | s-ink.  ar: optional Arabic line under the headline.
    { id: "hero", surface: "s-accent", headline: "Your headline here", sub: "One short line that says why it matters.", shot: "media/shot-1.png" },
    { id: "feature", surface: "s-bg", headline: "A second feature", sub: "Show it, don't describe it.", shot: "media/shot-2.png" },
  ],
};
