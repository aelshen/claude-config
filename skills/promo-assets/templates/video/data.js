// A short product video: hook → product (phone, a tap, the result) → proof → end card.
// Every number on screen comes from here; when it comes from a file, generate this with a build_data.py.
window.DATA = {
  size: /*SIZE*/,
  SAMPLE: true,
  hook: { kicker: "", headline: "Your hook in five words", sub: "One line of context." },
  product: {
    caption: "Tap anything to see what it does",
    sub: "A second line about the feature.",
    before: "media/shot-1.png",       // phone screen before the tap
    after: "media/shot-2.png",        // ...and after (same as before for no change)
    tap: { x: 0.5, y: 0.55 },         // where the tap lands, as a fraction of the screen
  },
  proof: { value: 1000, suffix: "+", label: "things you can show with a real number", chips: ["Fact one", "Fact two", "Fact three"] },
  end: { line: "", url: "" },         // empty: the brand's tagline and url
  durations: { hook: 3.5, product: 7.5, proof: 5, end: 4 },
};
