# Review rubric

## (F) Rubric for a 1-2 person team

Score each as Block / Fix / Nit / OK. Everything not about correctness defaults to Nit.

1. **Correctness and edge cases** (Block): logic, concurrency, null/empty/boundary inputs, data loss, migrations backward compatible.
2. **Security and data** (Block): authz scoping, secrets, injection, PII in logs, unsafe file paths, dependency risk.
3. **Error handling** (Fix): failures surface instead of being swallowed; specific exceptions; user-visible errors are actionable; retries bounded.
4. **Tests** (Fix): would the test fail if the code broke (Google)? Real collaborators where cheap; no weakened or deleted assertions; regression test for every bug fix.
5. **Simplicity** (Fix): no code without a current caller, no speculative abstraction, no duplicated helper, no dead code (Google "complexity").
6. **Consistency** (Nit, or Fix if it creates a second way of doing something): matches neighbouring code and the repo's house rules.
7. **Observability** (Fix for server paths): errors logged with context, no secrets in logs, one trace or request id; enough to debug a production failure alone.
8. **Performance** (Nit unless measured): N+1 queries, unbounded lists, blocking calls on hot paths, re-render storms.
9. **Maintainability fitness functions** (automated): complexity cap, no import cycles, duplication under threshold, no new `any` or `type: ignore`, dependency count. These run in CI and are the sustainable part of the rubric.
10. **Docs and comments**: comments explain why; README or AGENTS.md updated when commands or structure change.

