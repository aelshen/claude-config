# Deterministic tools

`scripts/sweep.sh` runs whichever of these are installed. Versions were current on 2026-10-12; use the project's pinned versions where it has them.

## (E) Deterministic tool stack (versions as returned by npm/PyPI on 2026-10-12)

Run these before any LLM review. They are cheap, deterministic, and keep the LLM on judgement.

**TypeScript / Expo (app/)**
- `npx tsc --noEmit` (typescript 7.0.2 on registry; use the project's pinned version). Type errors and API misuse.
- `npx eslint . --max-warnings 0` (eslint 10.12.0, typescript-eslint 8.71.2). For Expo: `npx expo lint`. Add `@typescript-eslint/no-floating-promises`, `no-explicit-any`, `ban-ts-comment`, `no-unused-vars`.
- `npx eslint-plugin-sonarjs` rules (4.2.2): `cognitive-complexity` (threshold 15), `no-duplicate-string`, `no-identical-functions`, `no-collapsible-if`. Enable only these four to avoid noise.
- `npx knip` (6.41.0): unused files, exports, dependencies, and unlisted deps. Replaces `ts-prune` (0.10.3, unmaintained). Review its output before deleting; framework entry points (Expo Router `app/` files) need `knip.json` entries.
- `npx jscpd --min-lines 8 --min-tokens 70 --threshold 3 src` (5.4.1): duplicate blocks.
- `npx depcruise src --validate` (dependency-cruiser 18.6.0): cycles and layer rules; add rules only if you have layers worth protecting.
- `npm test` (jest). Optional: `npx stryker run` (10.0.0) on one module at a time for mutation score.

**Python (server/)**
- `ruff check --select E,F,B,BLE,S,C4,SIM,UP,PL,TRY,ARG,RET,PERF,C90 .` and `ruff format --check .` (ruff 0.17.0). Highest value for AI slop: `BLE001, E722, S110, TRY, F401, F841, ARG, SIM, C901, PLR0912/0915`. Set `[tool.ruff.lint.mccabe] max-complexity = 10`.
- `.venv/bin/mypy .` (2.4.0) or `pyright` (1.1.414): types. Pick one.
- `vulture . --min-confidence 80` (2.16): dead code. Use a whitelist for FastAPI route handlers (decorators make them look unused).
- `radon cc -s -n C .` and `xenon --max-absolute B --max-modules A --max-average A .` (radon 6.0.1, xenon 0.9.3): complexity gate.
- `deptry .` (0.25.1): unused, missing and transitive dependencies.
- `semgrep --config p/python --config p/owasp-top-ten --error` (1.180.0) and `bandit -r server -ll` (1.9.4): security patterns.
- `.venv/bin/python -m pytest tests/`. Optional `mutmut run` (3.8.0) on a pure module. `import-linter` (2.15) if you have layer rules.

**SQL / other:** `npx supabase@latest db lint` for the sync schema.

**Cognitive complexity:** SonarSource's metric (sonarjs `cognitive-complexity`, default 15) fits readability better than cyclomatic. Use it for TS; ruff's `C901` (McCabe) plus radon for Python.

**Order of work:** format/autofix, then typecheck, then lint, then dead-code (knip/vulture), then duplication, then tests, then LLM review. Hand the LLM the tool output as a "do not re-report" list and as leads, rather than asking it to rediscover them. Claude Code's own docs say to exclude anything CI already enforces.

