---
name: codex-worker
description: "Run a Codex CLI job in a background worktree and resume it for follow-ups. Triggers include hand off to codex, codex job, codex implementer, delegate to codex and background codex."
---

# Codex worker

Give Codex well-specified builds, mechanical sweeps, triage and scoped reviews. Keep planning, ambiguous design, money, data and security decisions, and the final diff check in Claude. A build brief must say which fix to make.

## Write the brief

```text
Goal             Describe the fix or the question to answer.
Files it owns    List paths the worker may edit.
Acceptance       Give exact commands and expected results.
Leave alone      Name files, behavior and decisions outside scope.
Report           Summarize changes, test results and open questions.
                 Include the local path and ref of any clone or bundle.
```

## Run the job

Use this skill's `scripts/cw`, installed at `$HOME/.claude/skills/codex-worker/scripts/cw`.

1. Write the brief. Run `cw start "$repo" --brief "$brief" --mode build`. Save the printed ID and worktree path. Add `--prefetch pr:12 issue:34` to put GitHub context in `.cw/` before launch.
2. Use a Claude Code Monitor on `cw wait "$id" --max 3600`. Never use a sleep loop. Exit 0 means done, 1 means unsuccessful, and 2 means still running at the limit. Inspect a job with `cw status "$id"` or stop its process group with `cw kill "$id"`.
3. Run `cw collect "$id" --test "$checks"` with the acceptance command. It runs in the worktree outside Codex's sandbox. Read the result, the last 30 test lines and the exit code. Inspect the diff and new files yourself.
4. Commit in the worktree, push, open the PR and run the `codex-review` skill. Send verified findings back with `cw resume "$id" "Fix the finding in … and rerun …"`. Wait, collect and check the diff again.
5. After merge, run `cw clean "$id"`. It removes the worktree including uncommitted edits. Named branches and generated branches with commits outside the recorded base stay available.

Build uses `workspace-write` and `max` effort. Review and triage use `read-only` and `high`. Set `--effort` to override effort. Model selection uses `--model`, then `CW_MODEL`, then the CLI default. The timeout defaults to 60 minutes. Start and resume accept durations such as `--timeout 90s`. New branches start at `--base` (default `origin/main`). `--branch B` resets a named branch to the fetched `origin/B`.

## Traps

- Codex reads stdin even with a prompt. A plain background wrapper can take its children down on exit. `cw` detaches Codex and its watchdog and gives Codex `/dev/null` for stdin.
- The workspace-write sandbox cannot write a linked worktree's Git metadata and lacks network and `/dev/fd` access. Record affected checks in `tests.blocked_by_sandbox` and run them with `cw collect --test` from the caller.
- Codex sometimes leaves commits in another clone or a bundle. Collect prints `git pull --ff-only <path> <ref>` for discovered artifacts. Run the matching command in the job worktree and review the diff before committing.

## Ledger

Dashboards can read `cw status --json` or the atomically replaced files at `${CW_HOME:-$HOME/.claude/state/codex-jobs}/<id>.json`. Each records `id`, `name`, `repo`, `worktree`, `branch`, `base`, `mode`, `model`, `effort`, `sandbox`, `pid` (Codex process group), `watchdog_pid`, `session_id`, `started`, `ended` (Unix seconds for this attempt), `status`, `exit_code`, `timeout_s`, `brief`, `result_path` and `events_path`. Clean keeps the ledger.

Codex normally emits `{"type":"thread.started","thread_id":"<uuid>"}`. The worker checks the first 32 events for `thread_id`, `session_id` or a UUID-shaped `id`. Resume appends events and replaces `.cw/last.md`. Its result gives the worker's assessment (`done`, `blocked` or `partial`). [Result schema](assets/result.schema.json)
