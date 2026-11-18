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

When you know the acceptance check, make one background Bash call in Claude Code with `run_in_background` set to `true`.

```bash
cw run "$repo" --brief "$brief" --test "$checks"
```

The call prints the job ID and worktree, waits for the worker, then collects the result and runs the check in the worktree with the caller's access. It returns the check's exit code for a successful job or 1 for an unsuccessful job. Read the full diff and open new files yourself before committing.

The wait limit (`--max SECONDS`) defaults to the job timeout plus 60 seconds. If the wait reaches that limit (exit 2) or is interrupted (exit 130), use the printed ID with `cw wait "$id"`, then collect the result.

For longer jobs and follow-ups, use the individual commands.

1. Write the brief. Run `cw start "$repo" --brief "$brief" --mode build`. Save the printed ID and worktree path. Add `--prefetch pr:12 issue:34` to put GitHub context in `.cw/` before launch.
2. Use a Claude Code Monitor on `cw wait "$id" --max 3600`. Never use a sleep loop. Exit 0 means done, 1 means unsuccessful, and 2 means still running at the limit. Inspect a job with `cw status "$id"` or stop its process group with `cw kill "$id"`. Kill reports `stale` if it cannot verify that the job's watchdog owns the worker.
3. Run `cw collect "$id"` to read the result and see which files changed. Inspect the full diff and open the new files, including scripts and tests the acceptance command will execute. Once you approve those changes, run `cw collect "$id" --test "$checks"`. The command runs in the worktree with the caller's access. Read the last 30 test lines and the exit code.
4. Commit in the worktree, push, open the PR and run the `codex-review` skill. Send verified findings back with `cw resume "$id" "Fix the finding in … and rerun …"`. After each resume, wait and repeat step 3.
5. After merge, run `cw clean "$id"`. It removes the worktree including uncommitted edits. Named branches and generated branches with commits outside the recorded base stay available.

Start and resume honor `CODEX_SCOPE=off` in the source repository's `.github/codex-review.env`. Build uses `workspace-write` with network access disabled and `max` effort. Review and triage use `read-only` and `high`. Set `--effort` to override effort. Model selection uses `--model`, then `CW_MODEL`, then the CLI default. The timeout defaults to 60 minutes. Start and resume accept durations such as `--timeout 90s`. New branches start at `--base` (default `origin/main`). `--branch B` fetches branch `B` from origin and creates or fast-forwards the local branch. Local-only commits cause start to stop.

## Traps

- Codex reads stdin even with a prompt. A plain background wrapper can take its children down on exit. `cw` detaches Codex and its watchdog and gives Codex `/dev/null` for stdin.
- The workspace-write sandbox cannot write a linked worktree's Git metadata and lacks network and `/dev/fd` access. Record affected checks in `tests.blocked_by_sandbox` and run them after inspecting the changes in step 3.
- Codex sometimes leaves commits in another clone or a bundle. Collect prints `git pull --ff-only <path> <ref>` for discovered artifacts. Run the matching command in the job worktree and review the imported changes before running host checks.

## Ledger

Dashboards can read `cw status --json` or the atomically replaced files at `${CW_HOME:-$HOME/.claude/state/codex-jobs}/<id>.json`. Keep `CW_HOME` outside the worker's writable directories. Each ledger records `id`, `name`, `repo`, `worktree`, `branch`, `base`, `mode`, `model`, `effort`, `sandbox`, `pid` (Codex process group), `watchdog_pid`, `session_id`, `started`, `ended` (Unix seconds for this attempt), `status`, `exit_code`, `timeout_s`, `brief`, `result_path` and `events_path`. Clean keeps the ledger.

Codex normally emits `{"type":"thread.started","thread_id":"<uuid>"}`. The worker checks the first 32 events for `thread_id`, `session_id` or a UUID-shaped `id`. The state directory beside the ledger, named `<id>/`, holds `events.jsonl`, `stderr.log` and `last.md`. Resume appends to the logs and replaces the result. Clean removes this directory with the worktree. The result gives the worker's assessment (`done`, `blocked` or `partial`). [Result schema](assets/result.schema.json)
