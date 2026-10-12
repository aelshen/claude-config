# Safe refactoring protocol

## (D) Safe refactoring protocol

1. **Pin behaviour first.** Characterization (golden/snapshot) tests on the code you will touch; if coverage is thin, have an agent write tests, then verify them with mutation testing (Meta ACH style: target faults existing tests miss) or at least manual mutation of two or three lines. The tests are the spec. The agent may not edit them in the same step as production code.
2. **Isolate.** One refactor intent per branch, in a git worktree (subagent `isolation: "worktree"`), so a failed attempt is discarded for free. One logical change per commit; keep each PR small (a few hundred lines, one directory).
3. **Mechanical changes use codemods, not LLM edits.** Renames, import moves, API swaps: use the TypeScript language service, `jscodeshift`, ruff `--fix`, `ast-grep`, `semgrep --autofix`. Have the LLM write the codemod and run it, so the diff is uniform and reviewable. Google's migration work follows the pattern: find references with an index, edit, validate by build and tests, send failures to a human [P].
4. **Gate every step with deterministic checks** (typecheck, lint, tests) before the next edit. The type checker is the cheapest behaviour-preservation proof for renames and signature changes.
5. **Prove no behavioural diff.** Run the full suite; for pure refactors compare public outputs (API responses, snapshot of serialized output) before and after. RefactoringMiner (Java) can classify what actually changed. Mutation score should not drop.
6. **Constrain the agent.** Write the allowed file set and the forbidden changes into the prompt: no public-signature changes, no dependency changes, no test edits, no deleting files unless proven unreferenced (knip/vulture output cited). Cap diff size; abort and re-plan when it is exceeded. Require the agent to state the invariant it is preserving.
7. **Review the refactor as a refactor.** The reviewer should check "is behaviour unchanged" and "is the code simpler" (count of lines, branches, duplicated blocks before and after), not hunt new bugs.

