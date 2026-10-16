---
name: project-tracking
description: "One GitHub issue-and-board standard for every repo: issues with acceptance criteria, a Projects board (Backlog → Ready → In progress → In review → Done, Priority P0–P3), every PR linked to an issue, and drift between issues and the board found and fixed. Use to set a repo up, audit it, or run the day-to-day flow (open the issue, move the card, link the PR). Triggers on: set up issue tracking, project board, GitHub Projects, roadmap board, track this work, open an issue for this, move the card, board drift, audit tracking, is this repo tracked consistently, start of a session in a repo with .github/board.env."
---

# Project tracking

Every repo tracks work the same way, so any session (or person) can pick up any project:
**an issue for every change, a board that matches the issues, and a PR that names its issue.**
The standard lives here; repos carry only their own config and project-specific notes.

Why each rule exists (October 2026 audit of kuudoh, arabayya and playpatch):

- Unplanned work skipped the system. Ops, infra and handoff PRs went in with no issue: 21 of
  30 recent merged PRs in arabayya, 3 in kuudoh since adoption, every PR in playpatch. Nobody
  could see that work on a board. → **The one rule + a CI check.**
- Cards went stale: closed issues sat in In review for weeks because the board's built-in
  workflows were off. → **Workflows on + `board.sh sync`.**
- Priority as labels can't sort a board. → **Priority is a board field.**
- Each repo had its own drifting copy of `board.sh`, and both had the same bug (`move` right
  after `add` fails while item-list lags). → **One shared script; repos hold a shim and
  `.github/board.env`.**
- Titles like "fix thing (#322)" look linked but aren't: GitHub links only body keywords.
  → **`Closes #N` in the body.**

## The standard

1. **Every PR names an issue** in its body: `Closes #N`, or `Refs #N` / `Part of #N` when an
   issue takes several PRs (cross-repo `owner/repo#N` works). Unplanned work (ops, infra,
   hotfix) gets a short `type:chore` issue first, two lines is fine. The only exemption is
   the `no-issue` label, for notes or handoff-only PRs and dependency bumps.
   `.github/workflows/pr-links-issue.yml` enforces it when GitHub Actions can run. If Actions
   is unavailable (billing block, disabled org), the check silently never runs: jobs "fail"
   with zero steps. Then `board.sh sync` at session start is the only backstop, so don't skip it.
2. **Board columns** are exactly `Backlog, Ready, In progress, In review, Done`. **Priority** is
   a single-select board field `P0–P3`. The built-in workflows **Item closed**, **Pull request
   merged**, **Pull request linked to issue** and **Auto-add to project** are on.
3. **Labels**: `type:epic|feature|story|bug|chore|spike`, at least one `area:*` (per repo),
   `size:S|M|L`, `needs-spec`, `blocked`, `no-issue`, `agent:haiku|sonnet|opus` (implementer
   tier, matching the model tiering in CLAUDE.md). Full list with colours: `assets/labels.tsv`.
4. **Issues** come from forms with Context, Scope, Out of scope, **Acceptance criteria**,
   **How to verify** and Blocked by (`assets/ISSUE_TEMPLATE/`). Epics hold their tasks as
   native sub-issues; order between tasks goes in "Blocked by".
5. **Flow**: branch `t<N>-<slug>` → card In progress → PR with `Closes #N` → In review →
   squash-merge → Done (the workflows do the last moves; `sync` catches misses).
6. **Docs**: `docs/WORKFLOW.md` from `assets/WORKFLOW.md`. The shared part is identical in
   every repo; only the "Project-specific" section differs.

## Day to day (every session in a repo with `.github/board.env`)

- **Start:** `scripts/board.sh sync`. Fix drift with `--apply` (it only moves cards), and tell
  the user about unlinked merged PRs rather than inventing issues for old work.
- **Before writing code for a change:** find its issue (`gh issue list --search`), or open one
  with the matching form and `scripts/board.sh add <N> <Column> <P>`. Then
  `scripts/board.sh move <N> "In progress"` once the branch exists.
- **PR:** `Closes #N` in the body (the PR template starts with it), then
  `scripts/board.sh move <N> "In review"`.
- **Follow-ups you notice:** file them as issues (Backlog, with priority), don't fold them in.
- **End:** everything you touched is in the right column.

`board.sh add/move/prio` use `gh project item-add`, which is idempotent and returns the item id,
so they work immediately after creating an issue (item-list lags minutes behind adds).

## Set up or audit a repo

```bash
~/.claude/skills/project-tracking/scripts/audit.sh          # scorecard, no changes
~/.claude/skills/project-tracking/scripts/audit.sh --fix    # add only what's missing
```

`--fix` adds missing labels, forms, PR template, the PR check, `docs/WORKFLOW.md`,
`scripts/board.sh` (the shim) and the Priority field. It never overwrites a file or label. Then:

1. **Board**: create one if there is none (`gh project create --owner <repo owner> --title "<repo> roadmap"`,
   then link the repo with `gh project link`). The board must belong to the repo's owner: GitHub
   can't link a personal board to an org repo, so it never shows on the repo's Projects tab. Write `.github/board.env`:
   `BOARD_OWNER=`, `BOARD_PROJECT=`, `BOARD_SINCE=<the day after adoption>`. PRs merged
   before that aren't flagged. The date is inclusive and compared in UTC, so today's date would
   flag PRs merged earlier today, before the standard existed; west of UTC, an evening merge is
   already tomorrow in UTC, so use the day after that. A repo that has no PR check on purpose
   (a planning repo with hardly any PRs) sets `BOARD_PR_CHECK=off`.
2. **Status columns**: on a new, empty board set them by API (`updateProjectV2Field` with
   `singleSelectOptions` for the five names). That replaces the options, so on a board that
   already has cards rename them in the UI instead (existing card values may not survive).
   **By hand in the board UI** (no API): switch on the four workflows (Project → ⋯ → Workflows).
   The scripts are bash; run any label or field loop under bash, not zsh.
3. **Fill in `docs/WORKFLOW.md`** placeholders and its "Project-specific" section: area labels,
   roles, the repo's verify commands, hard rules. Put the repo's test commands into the
   `How to verify` default of the task form.
4. **Replace a local `scripts/board.sh`** with `assets/board-shim.sh` once the shared one does
   everything the local one did.
5. **Migrate priority labels** (if any) into the Priority field, then delete the labels:
   for each `P<n>` labelled issue, `scripts/board.sh prio <N> P<n>`. Setting a field adds the
   issue to the board if it isn't there, and a closed one lands with no Status, so run
   `scripts/board.sh sync --apply` **after** the migration to put those in Done.
6. Re-run `audit.sh` until it has no FAIL. Commit as one PR (with its own `type:chore` issue).

Change existing repo conventions only with the user's agreement, and in the session that owns
that repo. To audit someone else's repo read-only, point `BOARD_ENV` at a temp config:
`BOARD_ENV=/tmp/x.env audit.sh` (run from inside the repo).

## Public repos

Issues and PR bodies in a public repo are public. Never put private plans, customer names,
costs or security details in them.

- Public issues are for public bugs and requests, using the same labels and forms.
- Internal work is tracked in a **private companion repo** (`<repo>-planning`) on the same
  board. Public PRs reference it with `Refs owner/<repo>-planning#N`, which the PR check accepts
  and which shows only a number to outsiders. Keep outside-contributor templates (and their
  `CONTRIBUTING.md` flow) as they are; add the standard forms alongside them.
- Don't paste planning-issue titles or contents into public PR bodies or commit messages;
  describe the change itself. A cross-repo reference reveals only that the planning repo exists.
- Keep each design in one place: either its docs move into the planning repo with the issues,
  or they stay where they are and the issue links to them. Never split one design across both.
- A private planning repo needs Actions billing for any automation; the public repo's
  Actions minutes are free.

## CI minutes (private repos)

Private repos share the org's Actions minutes; in October 2026 three repos used up the free
2,000 halfway through the month. In every private repo's workflows:

- Run each job only when its part of the repo changes (`paths` / `paths-ignore`). Docs-only and
  HANDOFF-only changes run nothing.
- PR runs get `concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }`.
- Slow jobs (Docker builds, e2e) run only on `main`, on a `full-ci` label, or by hand
  (`workflow_dispatch`).
- Skip with a job-level `if:` rather than a step that exits early: a skipped job costs nothing,
  and every job that starts bills at least a minute.
- Path-filtered jobs can't be required status checks. On the free plan private repos have no
  branch protection, so this doesn't matter there.

The PR check (`pr-links-issue.yml`) has no checkout and runs only when the PR body or labels
change, not on every push; a job-level `if:` skips edits that leave the body alone and labels
other than `no-issue`.

Also budget GitHub's GraphQL limit (5,000 points an hour plus a burst limit, shared by every
session on the account): never run `board.sh list` or `sync` in a loop, and pace bulk board
edits. `gh api rate_limit` can say there is quota left while calls are being rejected. While
limited, `gh project` reports "unknown owner type", which is the limit, not a config problem.

## Changing the standard

Edit this skill (claude-config), not one repo's copy, then run `audit.sh` in each repo and
open a PR per repo for what changed. Keep the rules few: each one above answers a failure that
actually happened.
