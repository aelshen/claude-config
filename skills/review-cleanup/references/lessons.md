# Lessons from real runs

Things that went wrong or right in practice. Add to this when a run teaches something.

## 2026-10-12: whole-repo review of a 35k-line Expo + FastAPI app

- **Five finders, one per slice, in parallel worked well.** Slices: server request path, server
  tooling scripts, app screens, app logic layer, app components. Each finished in 40–140 s and
  found 13–15 items.
- **The same root cause showed up in several slices.** A paragraph splitter was copied six times
  across server modules, and an Arabic-marks regex eight times across the app, with a server copy
  too. A Supabase env lookup appeared in two reviewers' lists. Dedupe across slices before ranking.
- **"Unused" claims need checking.** Some were right, but several "dead" functions were used only
  by tests. Decide whether test-only code stays or goes, together with its tests; don't just delete it.
  A name grep can also match a longer name (`ListRow` inside `FlashcardListRow`). Grep with word
  boundaries (`grep -w`).
- **Shell gotcha:** in zsh, `grep --include=*.py` fails with "no matches found" because zsh expands
  the glob. Quote it (`--include='*.py'`) or pass file globs directly.
- **Deterministic tools would have saved effort.** Reviewers hand-found dead code and duplication
  that knip, vulture and jscpd report in seconds. Run the sweep first.
- **Reviewers found one real bug while looking for complexity:** an onboarding Skip that used an
  unsaved choice. Keep correctness in scope even on a "cleanup" review.
- **Live services ran from the working tree.** That meant the API (launchd), Metro and a symlinked
  config repo. Switching branches in the main checkout silently changed what the phone and the
  global config used. All cleanup ran in worktrees, with their own ports and scratch data copies.
- **Server refactors were proven by diffing JSON responses** from the old (live) and new (worktree)
  servers for the same requests, on top of the test suite.
- **Some differences that look like duplication are deliberate,** for example regex character
  ranges that differ for parity with another component. A finder should flag them as "check before
  merging", not "merge".

## 2026-10-13: whole-repo review of a 26k-line Python (FastAPI, SQLite) + Expo app

- **Six finders, one per slice (answer path, semantic layer, ingest pipeline, server, app Studio, app chat).** They took 3–10 minutes each. The slice holding the transactional core (change ledger) was slowest and the most valuable: it ran mutation checks on a repo copy and found untested guards whose mutants survived the full suite.
- **32 behaviour claims went to verifiers: 31 confirmed, 1 refuted.** Briefs that demanded executable proof (repro scripts on in-memory dbs or temp copies) produced claims that held up.
- **A finder's probe wrote into the real data dir.** It used a FastAPI TestClient against a test fixture, and a background job thread outlived the fixture's monkeypatched data dir. Add to every brief: "probes must not start background jobs or threads, or must join them before the fixture exits; run executable checks inside a `cp -cR` copy of the repo."
- **Point the sweep at the real source dirs.** Run from the repo root it also scanned 24 stale `.claude/worktrees/` copies, which multiplied ruff and vulture output by 25. Pass `checkpoint tests` explicitly, or exclude `.claude/`.
- **No uvx or pipx on the machine:** a throwaway venv in the scratchpad (`python3 -m venv; pip install ruff vulture radon`) kept the project untouched.
