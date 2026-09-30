---
name: session-handoff
description: "Write or update a handoff record so the next session (or person) can resume without re-deriving what you already know. Use when context is filling, when a chunk of work closes, before switching projects, or when asked to hand off. Triggers on: hand off, handoff, write up where we are, context is full, wrapping up, before I lose this session, catch up the next session, what's the state."
---

# Session handoff

A handoff is not a summary of what happened. It is the smallest set of facts that
stops the next session repeating your mistakes. Write for a competent stranger who
has the code and the git history and none of your memory, and who will otherwise
re-litigate decisions you already settled.

## Where it goes

Durability first, because a handoff that dies with the machine is worse than none:
someone trusted it.

1. If the repository has a working-notes directory that is tracked, put it there.
2. Otherwise `HANDOFF.md` at the repository root.
3. Only outside the repository if the work spans several repositories, and then say
   in each repository's README where it lives.

**Check the file is not ignored before you write to it.** Run
`git check-ignore -v <path>` and `git status --short <path>`. Scratch directories,
`.superpowers/`, anything under a `data/` rule, and most dotfolders are
ignored, and a handoff nobody can pull is a handoff nobody reads. If the right home
is ignored and you cannot change that, write the durable summary somewhere tracked
and leave the working notes where they are, with a pointer.

## What to write

Append a dated section. Never rewrite history: a superseded entry with a line saying
it was superseded is more useful than a clean file, because it tells the reader which
way the thinking moved.

Six things, in this order. Skip a heading only when it has nothing in it.

**State.** What is done, what is in flight, what is untouched. Name branches and
commit hashes, because a hash survives a description. Say whether everything is
pushed and clean.

**Decisions and why.** The reasoning, not the outcome. "We reverted X because it
measured worse on every axis and the measurement that settled it was Y" stops the
next session rebuilding X. An outcome without its reason gets reversed by the next
person with a good idea.

**Numbers, and which are stale.** Any figure you quote, with what produced it and
when. If a change has invalidated earlier figures, say so explicitly and in the same
place they appear. The most expensive failure in a long project is a number that
outlived the code that made it.

**Traps.** Environment facts that cost you time and are invisible in the code: a
service that must be stopped before a rebuild, a lock, a plan limit, an ignore
marker that does not exclude what its name implies, a process that must never be
killed by port. Each one is time the next session does not lose.

**Open and deferred.** What is unresolved, what was deliberately not done.
"Deliberately not done" prevents someone helpfully doing it.

**Next.** The first concrete action, specific enough to start without deciding
anything. Not "continue the migration" but "run X, expect Y, then Z".

## Before you write

Do not describe state you have not checked this turn. Verify, then write.

```bash
git -C <repo> log --oneline -3
git -C <repo> status --short
git -C <repo> rev-list --left-right --count @{u}...HEAD   # ahead/behind
```

Check any service the work depends on is actually up, and say so with the command
you ran. "The API is running" ages badly; "`curl -s -o /dev/null -w '%{http_code}'
localhost:8000/health` returned 200 at 14:20" does not.

## Make the next session find it

Writing the handoff is half the job. Nothing reads it automatically, and a handoff
with no pointer is a file nobody opens.

Two places load by themselves and both are keyed to the working directory, which is
also how the next session knows *which* handoff is theirs:

- **Project memory.** `~/.claude/projects/<slug>/memory/MEMORY.md` is loaded at
  session start for sessions launched in that directory. Add or update a one-line
  entry pointing at the handoff's path. This is the most reliable mechanism and the
  cheapest to maintain.
- **`CLAUDE.md` in the repository**, if one exists, which is loaded as project
  instructions. A single line naming the handoff is enough.

Add the pointer in the same turn you write the handoff. If neither mechanism is
available, say so to the user and tell them the path, so the knowledge at least
lives with a person rather than nowhere.

## Resuming from one

When a session opens on work you did not do, or the user asks where things stand,
read the handoff before acting. Then treat it as evidence rather than truth: it was
accurate when written and the repository has moved since. Re-run the state checks
above and reconcile. Where the document and the repository disagree, the repository
wins and the document needs a correction, which is itself the first useful thing you
can do in that session.

## Quality bar

Before finishing, read it as the stranger. If any sentence would make them ask "says
who?", add the evidence or cut the sentence. Two specific failures to check for:

- **Asserted verification.** "Tests pass" without the command and the counts. If you
  did not run it this turn, say when it was last run.
- **A claim you inherited.** If a figure came from someone else's report and you did
  not check it, attribute it. Handoffs are where unverified claims become facts.

Then say, in one line to the user, where you wrote it and what the next session
should do first.

## When not to use this

A handoff is for work that outlives the session. Do not write one for a task that
finished cleanly with nothing outstanding, and do not use it as a progress report
for someone watching you work. If everything is done, pushed, and there is no next
action, say that in the conversation instead.
