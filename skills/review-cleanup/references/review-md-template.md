# REVIEW.md

How code review works in this repo. Read by the `review-cleanup` skill and by reviewer agents.
Keep it short; promote anything that recurs into a lint rule or an AGENTS.md rule.

## What counts as Block
- Correctness bugs, data loss, security holes, broken migrations.
- <add repo-specific ones: e.g. "a word-type colour changed without re-validating the set">

## Deliberate patterns (don't flag)
- <e.g. "every external service sits behind a provider interface, even with one implementation">
- <e.g. "rule-ID comments (ALL-A-01) are intentional">

## Do not report
- Anything the linters/typecheck already enforce.
- <findings the owner rejected, with the date and reason>

## Justified complexity
- <file or area>: <why it stays complex> (<date>)

## Commands
- typecheck: <cmd>
- lint: <cmd>
- tests: <cmd>
- live services that run from the working tree (edit in a worktree): <list>
