# LLM-written-code smells: the checklist

Finders on the simplicity and tests lenses walk this list. Evidence level in brackets.

## (C) LLM code-smell catalogue

Evidence level in brackets. What to look for and how to catch it.

1. Broad `except Exception` / swallowed errors / fallback defaults that hide failure [measured: top smell in Liu]. Ruff `BLE001`, `E722`, `S110`, `TRY`. In TS: `no-empty`, `@typescript-eslint/no-floating-promises`, empty `catch`.
2. Duplicated helpers; reimplementing existing utilities [measured: 1.87x redundancy]. jscpd, grep for existing utilities; AGENTS.md list of canonical helpers.
3. Needless abstraction, wrapper layers, single-use interfaces, premature config [measured as bloat/God classes; Google "over-engineering"]. Complexity metrics; reviewer question "what is the second caller?"
4. Dead and unused code: unused vars, args, imports, exports, leftover files [measured]. Ruff `F401 F841 ARG`, vulture, knip.
5. Comment noise: comments narrating what the code does, stale TODOs, "changed X to Y" history comments [anecdotal; Google rule says comments explain why].
6. Inconsistent patterns versus neighbouring code [anecdotal; Google "consistency"]. Needs LLM judgement plus a conventions file.
7. Over-mocked tests that assert the mock [measured: 36% of agent commits add mocks]. Mutation testing; require at least one real-collaborator test.
8. Silently weakened tests: loosened assertions, `skip`, deleted cases, snapshot regeneration to make CI green [anecdotal; no study found]. Diff rule: any removed or loosened assertion needs a stated reason. Flag `.skip`, `xfail`, `--update-snapshot`.
9. Type escapes: `any`, `as unknown as`, `# type: ignore`, `@ts-ignore` added to silence checker [anecdotal]. Count them in the diff.
10. Scope creep: unrelated refactors or reformatting inside a task [anecdotal; Google asks for separate formatting changes].
11. Backwards-compat shims and flags for code that has no users [anecdotal].
12. Hallucinated APIs or config options, wrong library versions [anecdotal; caught by typecheck and build].
13. God files and scattered functionality from "modular mirage" [measured, small study].
14. Security smells: path traversal, unsafe format strings [measured in Liu]. Bandit, semgrep.
15. Verbose logging and redundant validation at every layer (defensive duplication) [anecdotal].

Guards in practice: a PostToolUse hook running ruff or eslint on edited files with failures fed back; a Stop hook running typecheck and tests; AGENTS.md rules ("no new `except Exception`", "reuse `app/src/lib/*` helpers", "no comments that restate code", list of canonical utilities); a REVIEW.md that excludes linter-catchable items; a periodic baseline lint of agent commits against human commits.

