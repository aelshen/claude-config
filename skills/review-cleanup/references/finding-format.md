# Finding format

Finders return findings in this shape, so they can be verified, deduped and ranked without
re-reading the code. Plain Markdown, one block per finding, numbered.

```
### <n>. <one-line claim>
- where: path/to/file.ts:120-148 (and any other locations)
- lens: simplicity | errors | tests | consistency | correctness | security
- severity: Block | Fix | Nit
- evidence: <the quoted line(s)>, plus the proof: the grep for callers and its result, the call path,
  or a failing test/script
- simpler version: <a short sketch or a precise description of the change>
- saves: ~<n> lines (or "0, clarity only")
- risk: low | med | high, and what to re-test
- kind: mechanical (typecheck/tests prove it) | refactor (needs its own PR) | decision (owner)
```

Then two short lists:
- **Leave alone:** complexity that looks heavy but is justified, with the reason.
- **Not checked:** files or areas in the slice the finder didn't read.

Rules:
- No evidence, no finding. "Unused" needs the grep that shows no callers, across the whole repo
  including tests and other packages.
- Quote code; don't paraphrase it.
- Don't report what the sweep tools already reported, unless adding the fix plan.
- Don't flag deliberate patterns listed in the context pack or `REVIEW.md`.

## Verifier verdicts

The verifier returns one line per finding:

```
<n>. CONFIRMED | REFUTED | UNSURE — <the lines or command output that decide it>
```
