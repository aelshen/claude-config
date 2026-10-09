/*!
 * promo.js: deterministic promo compositions for Side Quest projects.
 *
 * Two kinds of composition, both a single index.html:
 *   Promo.video({ width, height, fps, theme, scenes: [...] })   a timeline; seek(t) draws moment t
 *   Promo.boards({ width, height, theme, boards: [...] })       still images (App Store screenshots, link cards)
 *
 * A scene:  { id, duration, enter: 'cut'|'fade'|'rise', setup(el, ctx), render(t, el, ctx), checks: [seconds] }
 *   <section data-scene="id" class="s-bg"> holds its markup. render(t) gets scene-local seconds and must set every
 *   animated property on every call: no timers, Date.now, Math.random or CSS transitions (use Promo.random(seed)).
 * A board:  { id, setup(el, ctx) }   <section data-board="id">.
 *
 * Scripts (render.py, stills.py, export.py) drive the page through window.__promo. Opening index.html in a browser
 * gives a preview: space plays, arrows step a frame (shift: a second), #t=4.5 jumps, #b=<board> shows a board.
 */
(function (global) {
  "use strict";
  const B = global.PROMO_BRAND;
  if (!B) throw new Error("brand/brand.js didn't load: it must come before lib/promo.js");
  const RENDER = new URLSearchParams(location.search).has("render");

  // ---------- math ----------
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, p) => a + (b - a) * p;
  const ease = {
    linear: p => p,
    out: p => 1 - Math.pow(1 - p, 3),
    in: p => p * p * p,
    inOut: p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    outBack: p => { const c = 1.4; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); },
  };
  /** 0→1 over [start, start+dur], eased. */
  const prog = (t, start, dur, e = ease.out) => e(clamp((t - start) / (dur || 1e-6)));
  /** Critically damped spring from 0 to 1 starting at `start`; `speed` ~ 8–14. */
  const spring = (t, start, speed = 10) => { const x = Math.max(0, t - start) * speed; return 1 - (1 + x) * Math.exp(-x); };
  function random(seed) { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) >>> 0; let r = Math.imul(a ^ (a >>> 15), 1 | a);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r; return ((r ^ (r >>> 14)) >>> 0) / 4294967296; }; }

  // ---------- element helpers ----------
  const els = x => (typeof x === "string" ? [...document.querySelectorAll(x)] : x instanceof Element ? [x] : [...x]);
  function set(el, p) {
    const s = el.style;
    if ("opacity" in p) s.opacity = p.opacity;
    if ("x" in p || "y" in p || "scale" in p || "rotate" in p)
      s.transform = `translate(${p.x || 0}px, ${p.y || 0}px) scale(${p.scale ?? 1}) rotate(${p.rotate || 0}deg)`;
    if ("clip" in p) s.clipPath = p.clip;
    if ("blur" in p) s.filter = p.blur ? `blur(${p.blur}px)` : "";
  }
  const toggle = (el, cls, on) => el.classList.toggle(cls, !!on);

  /** Motion vocabulary. Each takes (targets, t, start, opts) and fully sets the targets for time t. */
  const fx = {
    fade(x, t, start, { dur = 0.5, to = 1, stagger = 0 } = {}) {
      els(x).forEach((el, i) => set(el, { opacity: to * prog(t, start + i * stagger, dur) }));
    },
    /** Rise into place: fade + move up `dist` px. */
    rise(x, t, start, { dur = 0.7, dist = 40, stagger = 0.08 } = {}) {
      els(x).forEach((el, i) => { const p = prog(t, start + i * stagger, dur); set(el, { opacity: p, y: (1 - p) * dist }); });
    },
    /** Spring scale-in for chips and badges. */
    pop(x, t, start, { stagger = 0.06, speed = 12 } = {}) {
      els(x).forEach((el, i) => { const s = spring(t, start + i * stagger, speed); set(el, { opacity: clamp(s * 3), scale: lerp(0.6, 1, s) }); });
    },
    /** Exit: fade out and drift up over `dur`. */
    out(x, t, start, { dur = 0.35, dist = 20 } = {}) {
      els(x).forEach(el => { const p = prog(t, start, dur, ease.in); if (p > 0) set(el, { opacity: 1 - p, y: -p * dist }); });
    },
    /** Reveal left→right (or right→left for RTL) with a clip mask. */
    wipe(x, t, start, { dur = 0.8, rtl = false } = {}) {
      els(x).forEach(el => { const p = prog(t, start, dur, ease.inOut) * 100;
        set(el, { clip: rtl ? `inset(0 0 0 ${100 - p}%)` : `inset(0 ${100 - p}% 0 0)` }); });
    },
    /** Type text at `cps` characters a second (works for Arabic: grapheme-safe). Returns true when done. */
    type(el, text, t, start, { cps = 18, caret = true } = {}) {
      const chars = [...new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(text)].map(s => s.segment);
      const n = Math.floor(clamp((t - start) * cps, 0, chars.length));
      const blink = caret && n < chars.length && t >= start ? "▍" : "";
      el.textContent = chars.slice(0, n).join("") + blink;
      return n === chars.length;
    },
    /** Count up to `value` over `dur`; fmt(n) formats it. */
    count(el, value, t, start, { dur = 1.4, fmt = n => Math.round(n).toLocaleString("en-US") } = {}) {
      el.textContent = fmt(value * prog(t, start, dur, ease.out));
    },
    /** A tap marker at (x, y) stage px: grows in, presses, fades. */
    tap(el, t, at, { x, y } = {}) {
      if (x != null) { el.style.left = x + "px"; el.style.top = y + "px"; }
      const a = t - at;
      if (a < -0.25 || a > 0.6) { set(el, { opacity: 0 }); return; }
      const p = a < 0 ? 1 + a / 0.25 : 1;
      set(el, { opacity: a > 0.3 ? 1 - (a - 0.3) / 0.3 : p, scale: a < 0 ? lerp(1.4, 1, p) : lerp(1, 0.8, clamp(a / 0.12)) });
    },
  };

  // ---------- brand ----------
  // Fonts: a brand may bring its own (brand.fonts = { sans: {family, files: [{src, weight, style}]}, arabic: {...} },
  // paths relative to the brand folder). Without them: Inter and Noto Naskh Arabic from fonts/.
  const FONT = { sans: (B.fonts && B.fonts.sans && B.fonts.sans.family) || "Inter",
                 arabic: (B.fonts && B.fonts.arabic && B.fonts.arabic.family) || "Noto Naskh Arabic" };
  function brandFonts() {
    const css = [];
    for (const f of Object.values(B.fonts || {})) for (const file of f.files || [])
      css.push(`@font-face { font-family: "${f.family}"; src: url("brand/${file.src}"); font-weight: ${file.weight || 400}; font-style: ${file.style || "normal"}; font-display: block; }`);
    if (css.length) { const st = document.createElement("style"); st.textContent = css.join("\n"); document.head.append(st); }
    const r = document.documentElement.style;
    r.setProperty("--font", `"${FONT.sans}", sans-serif`);
    r.setProperty("--font-ar", `"${FONT.arabic}", serif`);
  }
  function applyBrand(theme, width) {
    brandFonts();
    const c = B.themes[theme] || B.themes.light;
    const r = document.documentElement.style;
    for (const [k, v] of Object.entries(c)) r.setProperty("--" + k, v);
    document.getElementById("stage").style.setProperty("--u", width / 1080 + "px");
    document.querySelectorAll("img[data-logo]").forEach(img => {
      const src = (B.logos[theme] || B.logos.light)[img.dataset.logo];
      if (!src) throw new Error(`brand "${B.id}" has no "${img.dataset.logo}" logo`);
      img.src = "brand/" + src; img.alt = img.alt || B.name;
    });
  }

  async function fontsReady() {
    await Promise.all([`400 40px "${FONT.sans}"`, `700 40px "${FONT.sans}"`, `400 40px "${FONT.arabic}"`].map(f => document.fonts.load(f, "aب")));
    await document.fonts.ready;
    await Promise.all([...document.images].map(i => (i.complete ? null : new Promise(r => { i.onload = i.onerror = r; }))));
  }

  // ---------- lint ----------
  // Mechanical checks only: it can't judge story or taste; look at the stills for that.
  function lint(stage, W, H, theme) {
    const out = [];
    const add = (level, kind, el, msg) => out.push({ level, kind, msg, where: el ? describe(el) : "" });
    const palette = [...Object.values(B.themes[theme] || B.themes.light), ...(B.extraColors || []), "#ffffff", "#000000"].map(rgb);
    const safe = { l: W * 0.04, t: H * 0.04, r: W * 0.96, b: H * 0.96 };
    const sr = stage.getBoundingClientRect(), k = sr.width / W;
    const texts = [];
    for (const el of stage.querySelectorAll("*")) {
      if (!visible(el)) continue;
      if (el.tagName === "IMG" && !el.closest("[data-lint-ignore]") && el.complete && !el.naturalWidth) add("error", "image", el, `image didn't load: ${el.getAttribute("src")}`);
      const own = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).map(n => n.textContent.trim()).join(" ");
      if (!own || el.closest("[data-lint-ignore]")) continue;
      const cs = getComputedStyle(el), r = textRect(el);
      const box = { l: (r.left - sr.left) / k, t: (r.top - sr.top) / k, r: (r.right - sr.left) / k, b: (r.bottom - sr.top) / k };
      texts.push({ el, box, text: own });
      const label = `"${own.slice(0, 40)}"`;
      if (!el.closest("[data-bleed]") && (box.l < safe.l - 1 || box.t < safe.t - 1 || box.r > safe.r + 1 || box.b > safe.b + 1))
        add("warn", "safe-area", el, `${label} is outside the 4% safe area`);
      if (el.scrollWidth > el.clientWidth + 2 && cs.overflow !== "visible" || el.scrollHeight > el.clientHeight + 2 && /hidden|clip/.test(cs.overflowY))
        add("error", "clipped", el, `${label} is cut off`);
      const minPx = Math.min(W, H) * 0.022;
      if (parseFloat(cs.fontSize) < minPx) add("warn", "tiny", el, `${label} is ${parseFloat(cs.fontSize).toFixed(0)}px; under ${minPx.toFixed(0)}px is hard to read on a phone`);
      if (/[؀-ۿ]/.test(own) && !cs.fontFamily.includes(FONT.arabic)) add("error", "arabic", el, `${label} has Arabic but not the Arabic face: put it in lang="ar"`);
      if (![FONT.sans, FONT.arabic].includes(cs.fontFamily.split(",")[0].trim().replace(/^["']|["']$/g, ""))) add("warn", "font", el, `${label} uses ${cs.fontFamily.split(",")[0]}`);
      const col = rgb(cs.color);
      if (col && !el.closest("[data-viz]") && Math.min(...palette.map(p => dist(p, col))) > 12) add("warn", "color", el, `${label} color ${cs.color} isn't a brand color`);
    }
    for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
      const a = texts[i], b = texts[j];
      if (a.el.contains(b.el) || b.el.contains(a.el) || a.el.closest("[data-overlap-ok]") || b.el.closest("[data-overlap-ok]")) continue;
      const ox = Math.min(a.box.r, b.box.r) - Math.max(a.box.l, b.box.l), oy = Math.min(a.box.b, b.box.b) - Math.max(a.box.t, b.box.t);
      if (ox > 4 && oy > 4) add("warn", "overlap", a.el, `"${a.text.slice(0, 25)}" overlaps "${b.text.slice(0, 25)}"`);
    }
    const imgs = [...stage.querySelectorAll("img, .phone, [data-obstacle]")].filter(i => visible(i) && !i.closest("[data-overlap-ok]")).map(i => {
      const r = i.getBoundingClientRect(); return { el: i, box: { l: (r.left - sr.left) / k, t: (r.top - sr.top) / k, r: (r.right - sr.left) / k, b: (r.bottom - sr.top) / k } }; });
    for (const a of texts) for (const im of imgs) {
      if (a.el.closest("[data-overlap-ok]") || im.el.contains(a.el) || im.el.parentElement.contains(a.el)) continue;
      const ox = Math.min(a.box.r, im.box.r) - Math.max(a.box.l, im.box.l), oy = Math.min(a.box.b, im.box.b) - Math.max(a.box.t, im.box.t);
      if (ox > 4 && oy > 4) add("warn", "overlap", a.el, `"${a.text.slice(0, 25)}" runs into ${im.el.tagName === "IMG" ? "an image" : "the " + (im.el.className || "box")}`);
    }
    for (const f of document.fonts) if (f.status === "error") add("error", "font", null, `font failed to load: ${f.family}`);
    return out;
  }
  /** The box around the element's own text (not its full width), in viewport px. */
  function textRect(el) {
    let l = Infinity, t = Infinity, r = -Infinity, b = -Infinity;
    for (const n of el.childNodes) {
      if (n.nodeType !== 3 || !n.textContent.trim()) continue;
      const range = document.createRange(); range.selectNodeContents(n);
      for (const q of range.getClientRects()) { l = Math.min(l, q.left); t = Math.min(t, q.top); r = Math.max(r, q.right); b = Math.max(b, q.bottom); }
    }
    return l === Infinity ? el.getBoundingClientRect() : { left: l, top: t, right: r, bottom: b };
  }
  function visible(el) {
    for (let e = el; e && e.id !== "stage"; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === "none" || cs.visibility === "hidden" || parseFloat(cs.opacity) < 0.05) return false;
    }
    const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0;
  }
  function describe(el) { const s = el.closest("[data-scene],[data-board]"); const id = s ? (s.dataset.scene || s.dataset.board) : "";
    return `${id ? id + " › " : ""}${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""}${el.classList.length ? "." + [...el.classList].join(".") : ""}`; }
  function rgb(c) { if (!c) return null; if (c[0] === "#") { const h = c.length === 4 ? c.replace(/\w/g, x => x + x).slice(1) : c.slice(1);
    return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)); } const m = c.match(/[\d.]+/g); return m ? m.slice(0, 3).map(Number) : null; }
  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

  // ---------- stage + preview ----------
  function mountStage(W, H) {
    const stage = document.getElementById("stage");
    if (!stage) throw new Error('index.html needs <div id="stage">');
    stage.style.width = W + "px"; stage.style.height = H + "px";
    if (RENDER) return stage;
    const fit = () => { const k = Math.min(innerWidth / W, (innerHeight - 44) / H);
      stage.style.transform = `scale(${k})`; stage.style.left = (innerWidth - W * k) / 2 + "px"; stage.style.top = (innerHeight - 44 - H * k) / 2 + "px"; };
    addEventListener("resize", fit); fit();
    return stage;
  }

  // ---------- video ----------
  function video(comp) {
    const { width: W, height: H, fps = 30, theme = "light" } = comp;
    const ctx = { W, H, theme, brand: B, fx, ease, prog, spring, lerp, clamp, random, set, toggle };
    let t0 = 0;
    const scenes = comp.scenes.map(s => {
      const el = document.querySelector(`[data-scene="${s.id}"]`);
      if (!el) throw new Error(`no <section data-scene="${s.id}">`);
      const overlap = s.enter === "fade" || s.enter === "rise" ? (s.overlap ?? 0.4) : 0;
      const start = Math.max(0, t0 - overlap); t0 = start + s.duration;
      return { ...s, el, start, overlap };
    });
    const duration = t0;
    const stage = mountStage(W, H);
    applyBrand(theme, W);
    let built = false;
    const ready = fontsReady().then(() => { scenes.forEach(s => s.setup && s.setup(s.el, ctx)); built = true; return fontsReady(); });

    function draw(t) {
      for (const s of scenes) {
        const lt = t - s.start, on = lt >= 0 && lt < s.duration + (s === scenes[scenes.length - 1] ? 1e-3 : 0);
        s.el.style.display = on ? "" : "none";
        if (!on) continue;
        const e = s.overlap ? prog(lt, 0, s.overlap, ease.inOut) : 1;
        set(s.el, s.enter === "rise" ? { opacity: e, y: (1 - e) * 60 } : { opacity: e });
        s.el.style.zIndex = scenes.indexOf(s);
        s.render && s.render(clamp(lt, 0, s.duration), s.el, ctx);
      }
    }
    let cur = 0;
    const api = {
      kind: "video", width: W, height: H, fps, duration, theme,
      scenes: scenes.map(s => ({ id: s.id, start: s.start, duration: s.duration, checks: s.checks || [] })),
      ready, async seek(t) { await ready; cur = clamp(t, 0, duration); draw(cur); },
      lint() { return lint(stage, W, H, theme); },
    };
    global.__promo = api;
    if (!RENDER) ready.then(() => preview(api, () => cur, t => api.seek(t)));
    return api;
  }

  // ---------- boards ----------
  function boards(comp) {
    const { width: W, height: H, theme = "light" } = comp;
    const ctx = { W, H, theme, brand: B, set, toggle };
    const list = comp.boards.map(b => {
      const el = document.querySelector(`[data-board="${b.id}"]`);
      if (!el) throw new Error(`no <section data-board="${b.id}">`);
      return { ...b, el };
    });
    const stage = mountStage(W, H);
    applyBrand(theme, W);
    const ready = fontsReady().then(() => { list.forEach(b => b.setup && b.setup(b.el, ctx)); return fontsReady(); });
    let cur = list[0].id;
    const api = {
      kind: "boards", width: W, height: H, theme, boards: list.map(b => b.id), ready,
      async show(id) { await ready; cur = id; list.forEach(b => { b.el.style.display = b.id === id ? "" : "none"; }); },
      lint() { return lint(stage, W, H, theme); },
    };
    global.__promo = api;
    api.show((location.hash.match(/b=([\w-]+)/) || [])[1] || cur);
    if (!RENDER) ready.then(() => boardPreview(api, list.map(b => b.id)));
    return api;
  }

  // ---------- preview UI (browser only, never in renders) ----------
  function preview(api, now, seek) {
    const bar = document.createElement("div"); bar.id = "promo-bar";
    bar.innerHTML = `<button id="pp">▶</button><input id="ps" type="range" min="0" max="${api.duration}" step="${1 / api.fps}"><span id="pt"></span>`;
    document.body.append(bar);
    const ps = bar.querySelector("#ps"), pt = bar.querySelector("#pt"), pp = bar.querySelector("#pp");
    let playing = false, last = 0;
    const show = t => { seek(t); ps.value = t; pt.textContent = `${t.toFixed(2)} / ${api.duration.toFixed(2)}s`; history.replaceState(null, "", "#t=" + t.toFixed(2)); };
    const loop = ts => { if (!playing) return; const dt = last ? (ts - last) / 1000 : 0; last = ts;
      const t = now() + dt; if (t >= api.duration) { playing = false; pp.textContent = "▶"; show(api.duration); return; }
      show(t); requestAnimationFrame(loop); };
    const play = () => { playing = !playing; pp.textContent = playing ? "❚❚" : "▶"; last = 0; if (playing) { if (now() >= api.duration) show(0); requestAnimationFrame(loop); } };
    pp.onclick = play; ps.oninput = () => { playing = false; show(+ps.value); };
    addEventListener("keydown", e => {
      if (e.code === "Space") { e.preventDefault(); play(); }
      if (e.code === "ArrowRight" || e.code === "ArrowLeft") { playing = false; show(clamp(now() + (e.code === "ArrowRight" ? 1 : -1) * (e.shiftKey ? 1 : 1 / api.fps), 0, api.duration)); }
    });
    show(+(location.hash.match(/t=([\d.]+)/) || [])[1] || 0);
  }
  function boardPreview(api, ids) {
    const bar = document.createElement("div"); bar.id = "promo-bar";
    bar.innerHTML = ids.map(id => `<button data-b="${id}">${id}</button>`).join("");
    document.body.append(bar);
    bar.onclick = e => { const id = e.target.dataset.b; if (id) { api.show(id); history.replaceState(null, "", "#b=" + id); } };
  }

  global.Promo = { video, boards, fx, ease, prog, spring, lerp, clamp, random, set, toggle, brand: B };
})(window);
