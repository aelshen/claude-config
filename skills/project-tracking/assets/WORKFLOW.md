# How work is tracked here

<!-- From the project-tracking skill (claude-config). Everything outside the
"Project-specific" sections is the shared standard: change it in the skill, not
here, so every repo stays the same. -->

Work is GitHub Issues on `OWNER/REPO`, tracked on the **BOARD NAME** GitHub Project:
BOARD URL. Cards move with `scripts/board.sh` (needs `gh` with the `project` scope:
`gh auth refresh -s project`).

```bash
scripts/board.sh add  <N> [Column] [P0-P3]   # add an issue (idempotent; default Backlog)
scripts/board.sh move <N> <Column>           # Backlog | Ready | "In progress" | "In review" | Done
scripts/board.sh prio <N> <P0-P3>
scripts/board.sh list [Column]
scripts/board.sh sync [--apply]              # find and fix drift between issues and the board
```

## The one rule

**Every PR names an issue** (`Closes #N`, or `Refs #N` when an issue takes several PRs).
That includes unplanned work: ops, infra, hotfixes. Open a short `type:chore` issue first; two
lines is enough. The only exemptions carry the `no-issue` label: notes or handoff-only PRs and
dependency bumps. CI enforces this (`.github/workflows/pr-links-issue.yml`).

## Hierarchy

- **Epic** (`type:epic`, title `Epic: …`): one initiative. Its tasks are native **sub-issues**,
  so the board shows progress.
- **Task** (`type:story` / `type:feature` / `type:chore` / `type:spike`): one slice, one PR.
  Order between tasks goes in "Blocked by".
- **Bug** (`type:bug`): standalone, or a sub-issue of an epic.

## Board

Columns: **Backlog → Ready → In progress → In review → Done.** Priority is a board field,
**P0** (now) to **P3** (later), so the board sorts by it.

- **Backlog**: captured; may be `needs-spec`.
- **Ready**: every form section filled, acceptance criteria checkable, no `needs-spec` or
  `blocked`, everything in "Blocked by" merged.
- **In progress**: a branch exists. **In review**: a PR is open.
- **Done**: merged (or closed), and the reviewer checked every acceptance criterion.

The board's built-in workflows are on: item closed → Done, PR merged → Done, PR linked → In
review, auto-add. `board.sh sync` catches anything they miss.

## Labels

`type:*` (above) · `area:*` (see project-specific) · `size:S|M|L` (L: split before Ready) ·
`needs-spec` · `blocked` · `no-issue` · `agent:haiku|sonnet|opus` (implementer tier, when a
sub-agent builds it).

## Flow

1. **Plan**: the planning session writes or refines issues, marks them Ready, sets Priority.
2. **Build**: branch `t<N>-<slug>` off the latest `main`; `scripts/board.sh move N "In progress"`.
   Implement only the issue's scope; adjacent problems go in the PR's notes as follow-ups.
3. **Verify**: run the issue's "How to verify".
4. **PR**: `Closes #N` in the description; `scripts/board.sh move N "In review"`.
5. **Review & merge**: check every acceptance criterion, squash-merge, confirm it landed on
   `main`, file follow-ups as issues.

**Session hygiene (agents):** at the start of a session run `scripts/board.sh sync` and fix or
report drift; before ending, make sure everything you touched is in the right column.

## Project-specific

<!-- area:* labels, roles (who plans/reviews/merges), the repo's verify commands, hard rules
(privacy, money, data), and where non-public planning lives if the repo is public. -->
