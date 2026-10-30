---
name: codex-review
description: "Peer review by Codex (OpenAI's CLI) on every PR before it merges, in every repo: one shared script, per-repo scope (.github/codex-review.env), findings verified before acting, a 'Codex review' section in the PR, a merge guard hook, and one log with a report. Use before merging any PR, when setting a repo up for it, or to see whether it earns its keep. Triggers on: codex review, peer review, second opinion review, before merge, review this PR with codex, is codex worth it, codex-review report."
---

# Codex peer review

A second model reviews every PR's committed diff before merge. It sees what the author's model missed: the cache
key a prompt change forgot, the second code path, the audit field that is always empty, a privacy leak in telemetry.

Why (pilot, 2026-10-30, playpatch + checkpoint): 12 PRs, 20 rounds, 12 findings, 11 real, 1 declined; no finding on
clean PRs; 30 s to 4 min a round. The best catches were in code a "risky paths only" list would have skipped (answer
prompts, telemetry), so the default scope is **all**. Codex never sees data: a linking or projection change still needs
its measurement on real data, and tests still run. Two rounds catch nearly everything; later rounds drift to judgement
calls.

## The flow (every PR)

1. Commit, push, open the PR. Then run `scripts/codex-review.sh` on the branch (the stub runs
   `~/.claude/skills/codex-review/scripts/codex-review.sh`). It refuses a dirty tree: only committed work leaves the machine.
2. **Findings are leads.** Check each against the code, a test or the data. Fix it, or decline it in the PR with the
   reason. Never apply a finding unread.
3. If you changed code, run it again (round 2). Stop there; a round 3 only to check a P1 fix. Disagreements that
   matter go to the owner.
4. The PR body gets a **`## Codex review`** section: rounds, each finding, real or not, fixed or declined and why.
   A clean round is one line: `Codex review: 1 round, no findings.` A skip: `Codex review: skipped (<the script's reason>).`
5. When the PR is settled: `scripts/codex-review.sh mark <pr> <real> <noise> "note"`.
6. Merge only after CI has finished. The merge guard (`scripts/merge-guard.sh`, a PreToolUse hook) refuses
   `gh pr merge` in a configured repo while a check is pending, before any check is registered (right after a push
   `gh pr checks --watch` returns at once), on failed checks, or without the section. `CODEX_GUARD=off gh pr merge ...`
   overrides it for one command.

## Setting a repo up

- `scripts/codex-review.sh`: copy `assets/stub.sh`.
- `.github/codex-review.env`:
  ```
  CODEX_SCOPE=all            # all | risky | off
  CODEX_PATHS=""             # risky: review only when a changed file matches (bash patterns, * matches /)
  CODEX_EXCLUDE="tests/golden/* app/src/i18n/*"   # changes only here never trigger a review
  CODEX_REQUIRE_CI=1         # 0 for a repo with no CI, so the merge guard doesn't wait for checks
  ```
- The repo's AGENTS.md says where its review rules are (REVIEW.md, deliberate patterns). Codex reads it; shared
  guidance is `~/.codex/AGENTS.md` (from `assets/codex-AGENTS.md`).
- A repo whose code may not go to OpenAI is `CODEX_SCOPE=off` until the owner says otherwise.

Per repo (owner, 2026-10-30): playpatch `all`, checkpoint `all`, arabayya and delphi `risky` (paths in their env
files), kuudoh `off` pending the owner's OK to send its source to OpenAI.

## Measuring

`codex-review.sh report [days]`: per repo PRs, rounds, findings and P1s (counted from each run's verdict), real and
noise (from `mark`), average seconds. Log: `~/.claude/state/codex-review/{runs,marks}.tsv`, outside every repo.
Cost: the CLI runs on the ChatGPT plan login; check usage with `/status` in `codex` after a busy week.

## Traps

- `codex review --base` takes no custom instructions (a prompt with `--base` is rejected): guidance goes in AGENTS.md.
- Codex's sandbox has no sockets: server-starting tests fail there (the shared guidance says so).
- Docs-only PRs may run only the links check: "pending" means a check is running, not that one is missing.
- A log file inside the repo dirties the tree and the next run refuses: state lives outside.
