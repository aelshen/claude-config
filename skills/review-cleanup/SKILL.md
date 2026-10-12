---
name: review-cleanup
description: "Review a codebase or a diff for quality with parallel reviewer subagents, verify every finding, rank them, and (on approval) clean up in small, behaviour-preserving, tested steps. For making LLM-written code simpler, tidier and production-ready: dead code, duplication, needless abstraction, swallowed errors, weak tests, inconsistent patterns, plus correctness and security. Triggers on: code review, quality review, cleanup pass, tidy the codebase, simplify, refactor safely, AI slop, tech debt sweep, review before merge, is this production ready."
---

# Review and cleanup

A review is only worth what survives verification. The leading systems (Claude Code Review, Cursor
Bugbot, Qodo, ByteDance BitsAI-CR) share one shape: **cheap deterministic tools first, several
independent finders with disjoint lenses, a separate skeptical verifier per finding, dedupe and rank,
a human gate, then fixes in small gated steps.** Unverified LLM review sits around 50–70% precision
at best, and judges systematically over-flag correct code; verification and evidence rules are what
make it usable. Sources and numbers: `references/research.md`.

This skill has two modes. Pick from the request; ask only if it's truly unclear.

- **Review** (default): find, verify, rank, report. No edits.
- **Cleanup**: review, then apply the items the user approves, one at a time, in an isolated worktree.

For a quick correctness pass on one PR, the built-in `/code-review` (or `/security-review`) is enough.
Use this skill for whole-repo or whole-area quality, for cleanup, and when findings will be acted on.

## Stage 0: scope and baseline

1. **Target.** A diff (`git diff <base>...HEAD`), a path list, or the whole repo. For a whole repo,
   split into **slices of roughly 3–8k lines with clear seams** (request path vs tooling scripts;
   screens vs logic vs components). Slices are the unit of parallel review.
2. **Read the house rules** once: `AGENTS.md`, `CLAUDE.md`, `REVIEW.md` if present, and any
   rules register. Write a short **context pack** (10–30 lines): stack and versions, deliberate
   patterns not to flag (for example "every external service sits behind a provider interface"),
   commands for typecheck, lint and tests, and the do-not-report list from `REVIEW.md`.
3. **Live systems.** Find out what runs from the working tree (dev servers, launchd jobs, Metro,
   symlinked config). If anything does, **all edits happen in a worktree** and the main checkout
   is never switched. Write this into every brief.
4. **Baseline.** Run the test suite and record pass/fail counts. **If tests are red at baseline,
   stop and report**: cleanup needs a green baseline to prove nothing changed.

## Stage 1: deterministic sweep

Run `scripts/sweep.sh <repo-or-path> <out-dir>`. It detects TypeScript/JavaScript and Python and runs
whichever of these are installed (it never installs anything): typecheck, linters with the AI-slop
rules, dead-code finders (knip, vulture), duplication (jscpd), complexity (radon) and security
(semgrep, bandit). Missing tools are listed with the command to add them. Exact commands and
rule sets: `references/tools.md`.

The output in `<out-dir>` is **leads and a do-not-re-report list** for the finders, not findings.
Tool output still needs judgement: knip and vulture flag framework entry points (routes, decorators,
expo-router files), and test-only use looks "unused" to some tools.

## Stage 2: parallel finders

Launch one finder per **slice**, all in one message so they run in parallel. Use the `review-finder`
agent (Sonnet, read-only). Each brief contains:
- the slice's files and the context pack;
- that slice's lines from the sweep output, as leads;
- the lenses to apply (below) and the smell checklist (`references/smells.md`);
- the evidence rule: **every finding has `file:line`, the quoted code, and the proof (the grep
  for callers, the call path, or the test that shows it). No evidence, no finding;**
- the output format in `references/finding-format.md`, and a cap (top 10–15 per slice).

Lenses (a finder applies all that fit its slice; for a small diff, use one finder per lens):
1. **Simplicity:** dead code, duplication, needless abstraction, long functions, flag soup.
2. **Error handling and resilience:** swallowed or broad exceptions, fallbacks that hide failure,
   unbounded retries, missing timeouts, observability on server paths.
3. **Tests:** would the test fail if the code broke? Over-mocking, weakened or skipped assertions,
   missing regression tests.
4. **Consistency:** two ways of doing the same job, drift from neighbouring code and house rules.
5. **Correctness and security** (use Opus via `ultrathink-debugger`, or the built-in `/code-review`,
   for these when the diff touches logic, auth, data or money).

Rubric and severities (Block / Fix / Nit): `references/rubric.md`. Everything that isn't
correctness, security or data loss defaults to Fix or Nit.

## Stage 3: verify every finding

Before anything reaches the user, **each finding gets an independent check**:
- **Cheap claims are verified by you, directly.** "Unused", "only one caller" and "duplicated in N
  places" are a grep each. Run it yourself. Reviewers often miss callers in other packages, tests,
  dynamic imports or string-based registries.
- **Judgement claims go to the `review-verifier` agent** (skeptical, read-only). Batch 5–10 findings
  per verifier. Give it the claim and location only, not the finder's reasoning, to avoid anchoring.
  It returns CONFIRMED, REFUTED or UNSURE, with the lines that prove it. **Drop REFUTED. Drop or
  downgrade UNSURE.**
- Where a claim is about behaviour ("this crashes on empty input"), verify it **executably**: a
  failing test or a one-off script. A finding with a failing test is worth ten without.

## Stage 4: dedupe, rank, report

- Merge findings that share a root cause across slices (the same helper copied into server and app;
  one regex in eight files). Keep the best-evidenced copy, and note which slices agreed: agreement
  is a confidence signal.
- Rank by severity, then confidence, then value (lines removed or bugs prevented) against risk.
- Split into **"safe mechanical cleanups"** (no behaviour change, provable by typecheck and tests),
  **"worth doing, needs its own PR"** (bigger refactors with a test plan), **"needs the owner's
  decision"** (deleting features, changing behaviour), and **"leave alone"** (complexity that's
  justified: say why, so the next review doesn't re-flag it).
- Report in plain language: what's wrong, the simpler version, lines saved, risk. Cap it: all
  Blocks, the top Fixes, a count of Nits. Pre-existing issues outside a diff's scope go to a
  backlog list, not the fix list.

**In review mode, stop here.** Offer cleanup.

## Stage 5: cleanup loop (approved items only)

Follow `references/refactor-protocol.md`. In short:
- **Waves.** Wave 1 = the safe mechanical batch, one PR per area (for example server, app). Wave 2 =
  each bigger refactor as its own PR, in order of value. Owner decisions are applied only as decided.
- **Isolation.** Each wave runs in a worktree (`implementer` agent with `isolation: "worktree"`), on
  its own branch, with its own dev server on a spare port and a scratch copy of any data. It never
  touches live services, the main checkout, or production data.
- **Constraints in the brief:**
  - the allowed files;
  - no test edits except for removed features (and say which);
  - no dependency or public-interface changes unless approved;
  - verify each claim again before changing it, and skip any that's wrong;
  - prefer codemods (ruff `--fix`, ast-grep, TS language service) for mechanical edits.
- **Gates after every item:** typecheck, lint, tests. For server refactors, **diff real responses**
  from the old and new server for the same requests. For UI, check the screens touched (390×844 web
  or device).
- **Your review of the result:** read the diff yourself. Check behaviour unchanged, scope respected,
  no weakened or deleted tests, no new type escapes (`any`, `# type: ignore`), and the line count
  actually went down. Then CI, merge, and restart anything that runs from the main checkout.

## Stop rules

- At most **two** review→fix rounds. After the first, report only Block and Fix: no new nits.
- Stop when a round yields nothing that survives verification.
- Stop and ask on: a test going red that was green at baseline, any public-interface, dependency or
  test-file change, a deletion of user-visible behaviour, or a verifier UNSURE on a Block.
- Cap each cleanup item's diff (about 400 lines). Split anything bigger.

## Learn from each run

Append to the repo's `REVIEW.md` (create it from `references/review-md-template.md` if missing):
- findings the owner rejected, and why, so they go on the do-not-report list;
- complexity judged justified, so it isn't flagged again;
- recurring smells worth a lint rule or an `AGENTS.md` rule. The sustainable fix for a smell is a
  rule that stops it coming back, not another review.

## Cost

Finders and verifiers run on Sonnet; Haiku (`Explore`) only gathers files and call sites; Opus (the
main session) writes briefs, verifies cheap claims, ranks, reviews diffs and talks to the user. A
whole-repo review of about 35k lines took five finders in parallel, plus verification, in under
three minutes.
