# Research: agentic code review and cleanup (October 2026)

The evidence behind this skill, gathered 2026-10-12. Tags: [P] primary source, [S] secondary, [V] vendor claim, [U] unverified. Re-check numbers before quoting them.

## (A) Tools landscape

| Tool | Scope | How it works | False-positive controls | Cleanup vs bug finding |
|---|---|---|---|---|
| Claude Code `/code-review` (alias `/review` since v2.1.223) [P docs] | Diff plus surrounding code, local | Runs as a background forked subagent. Effort levels low..max: low reports only the most confident findings, medium..max broaden coverage. `--fix`, `--comment`, `--max-findings`. `ultra` runs a cloud multi-agent review. | Verification step; effort tier | Correctness first. At higher effort it also covers reuse, simplification and efficiency. `/simplify` is a separate cleanup-only pass that applies fixes. |
| Claude Code Review (managed GitHub app, Team/Enterprise preview) [P docs] | PR plus full codebase | Parallel agents, each on a different class of issue, then a verification step against actual code behaviour, then dedupe and severity ranking. About 20 min and $15-25 per review. Severity: Important, Nit, Pre-existing. Never blocks merge. | Verification agents; REVIEW.md can set a "verification bar" (file:line evidence), nit caps, skip rules, and "after first review, Important only" convergence; 👍/👎 feedback tuning | Defaults to correctness only. CLAUDE.md violations become nits. |
| Open-source `code-review` plugin (anthropics/claude-code) [P] | Diff | Haiku eligibility check, Haiku CLAUDE.md discovery, Sonnet summary, then 4 parallel reviewers (2 Sonnet on CLAUDE.md, 2 Opus on bugs: one diff-only, one on changed lines). Each finding is re-checked by a separate validator subagent (Opus for bugs, Sonnet for rules). Failed findings are dropped. | Validator subagents, binary pass/fail. The current command file has no numeric score. Older descriptions mention a 0-100 score with an 80 threshold [S]. | Explicit exclusions: pre-existing issues, linter-catchable, pedantic nits, subjective style, input-dependent speculation |
| OpenAI Codex review [P docs, V] | PR, repo-wide navigation | GPT-5-Codex is trained for review; it navigates the repo, reasons over dependencies, and can run code and tests. Reports only P0/P1 on GitHub. Closest AGENTS.md per changed file gives review rules. OpenAI says Codex reviews 100% of its own PRs. | Severity cut (P0/P1 only); trained model; execution as evidence | Bug-focused. Lower severities only if AGENTS.md raises them. |
| GitHub Copilot code review [P changelog, S] | PR plus repo | Agentic tool-calling to gather context, runs on GitHub Actions since 2026-03. Linters and CodeQL integration announced (Oct 2025); ship date [U]. | Deterministic tools in the loop | Mixed |
| Cursor Bugbot [P Cursor blog] | PR | v1 (Jul 2025): 8 parallel passes with randomised diff order, majority vote (drop findings flagged once), merge, validator model, category filter, dedupe against earlier runs. Fall 2025: fully agentic, the agent decides where to dig. | Voting, validator, resolution-rate metric (AI-judged "was the bug fixed at merge") | Bugs only. Resolution rate 52% to over 70% over 40 experiments; resolved bugs per PR about 0.2 to 0.5; v11 in Jan 2026. |
| CodeRabbit [S, V] | PR-scoped plus context | Combines LLM reasoning with 40+ linters/analysers. Strong on the Martian benchmark, vendor-reported. | Static analysers pre-feed the LLM | Both |
| Greptile [V] | Whole repo graph | Indexes functions, classes and callers into a graph. v3 is agentic. Learns from 👍/👎 and comments. | Learned team preferences. Self-reported action rate 34.75% to 59.24% (v2 to v3). | Mostly bugs |
| Graphite Diamond / Agent [V, S] | PR (stacked PRs) | Claude-based. Claims 5-8% false positives (guide) or "sub-3%" in another guide [U]; 67% implementation rate of suggestions. | Acceptance-rate tracking | Both |
| Qodo (PR-Agent open source, Merge, 2.0) [V] | PR plus repo | 2.0 moved from one LLM call returning YAML suggestions to specialist agents (bugs, quality, security, test gaps) with dedupe and a judge [S]. Claims F1 60.1% on its own benchmark [V]. | Judge agent, compliance checks | Test-gap analysis is a first-class feature |
| Amp (Sourcegraph spin-out) [S] | Diff in editor | Dedicated review agent with a review-specific toolset, "filters low-signal feedback" | Filtering | Both |
| Google Jules critic [P blog] | Generation-time | Adversarial critic reviews each change before completion and returns objections to the agent; initial version is single-pass | Critic is separate from author | Quality gate during generation |
| Google (migrations) [P arXiv 2504.09691] | Repo-scale | LLM-driven migrations use Kythe indexing to locate references and run multi-stage validation (build, tests). Failures are routed to humans. Developers estimate about 50% less migration time. A secondary summary says 39 migrations and 595 changes [U]. | Deterministic validation after every edit | Refactoring at scale |
| Meta [P FSE'26 industry paper, arXiv 2501.12862] | Review comments to patches; tests | MetaMateCR turns reviewer comments into patches (fine-tuned Llama; ActionableToApplied 19.7% in production). ACH is mutation-guided LLM test generation: engineers accepted 73% of its tests. | Reviewer-in-loop; mutation targets only undetected faults | Test hardening |
| ByteDance BitsAI-CR [P arXiv 2501.15134] | Function-level hunk context | RuleChecker (fine-tuned, 219-rule taxonomy), then ReviewFilter (yes/no judge), then embedding dedupe. Precision 75% peak; "outdated rate" (the flagged lines get changed) as an acceptance proxy. | Two-stage generate-then-filter; precision over recall | Rule taxonomy |

Common architecture across the leaders: (1) several independent finders, (2) a separate verifier or voting step, (3) dedupe and severity rank, (4) repo-level rules file, (5) a feedback loop. The industry converged on "generate wide, verify hard, report narrow."


## (B) Evidence on what works

- **Verification and voting cut noise.** Cursor: single-vote findings dropped plus a validator model [P]. Anthropic: a verification agent per candidate [P docs]. BitsAI-CR: the filter stage lifted offline precision from 57.0% to 65.6% [P]. Anthropic reports that substantive comments on PRs went from 16% to 54% and under 1% of findings are marked wrong by engineers [S, V; not in the docs page].
- **Agentic beats fixed pipelines.** Cursor's largest gain came from letting the agent investigate [P]. Copilot and Greptile moved the same way [S, V]. Prompts held back "to avoid false positives" lost recall without helping precision.
- **Precision of reviewers is middling and vendor-dependent.** Martian benchmark: offline 50 curated PRs plus an online set tracking which comments developers actually act on. CodeRabbit top F1 about 51%; Bugbot highest precision 68.9% but lower recall; no tool above roughly 63% recall in its first run [V/S]. Qodo claims F1 60.1% on its own set [V]. Claude Code was said to reach about 51% recall at much lower precision in Augment's write-up, which is a competitor [S]. Expect a 50-70% share of comments acted on for the best systems, much less for default settings.
- **Failure modes are real.** LLM judges over-flag correct code as non-conforming ("systematic overcorrection"). More elaborate prompts that demand explanations and fixes raise the misjudgment rate [P arXiv 2603.00539, ASE'25 2508.12358]. Proposed remedy: test the model's proposed fix executably. HalluJudge (arXiv 2601.19072) defines review hallucinations as ungrounded, irrelevant or misaligned comments that can't be caught by compiling. CR-Bench (arXiv 2603.11078, Mar 2026): agents tuned to find all hidden issues have a low signal-to-noise ratio, and resolution-only metrics hide the cost [P abstract].
- **Single vs multi-agent.** CR-Bench's preliminary study compared single-shot with Reflexion-style agents. A multi-agent thesis found broader coverage and less redundancy [S]. Industry practice favours multiple finders with one verifier. I found no rigorous independent head-to-head [U].
- **Benchmarks.** CR-Bench (2603.11078), GitHub's ReviewBench (219 PRs, grounded F1; vendor-run) [S], CodeFuse-CR-Bench, ContextCRBench (context-rich), Martian offline/online, Cursor's BugBench (internal). There is no SWE-bench equivalent that is both independent and accepted.
- **Agent-written code quality.**
  - Liu et al. (arXiv 2603.28592, MSR'26): 302,579 AI-authored commits, 6,299 repos. 89.3% of the 484,366 issues were smells (top: broad exception handling 41,374; unused variables; unused arguments). 22.7% of AI-introduced issues still at HEAD. AI introduced about 1.5x more correctness issues than it fixed. [S via blog; paper not read directly]
  - Huang et al. (arXiv 2601.21276, MSR'26): redundancy in AI PRs 1.87x human, yet reviewers were more positive about them [S].
  - Hora and Robbes (arXiv 2602.00409, MSR'26): 1.2M commits. 36% of agent commits add mocks vs 26% for non-agent; 23% touch tests vs 13% [P abstract].
  - arXiv 2601.20109: after normalising by churn, agents don't differ on issues; smells dominate [P abstract]. arXiv 2605.02741: more capable models gave bloated, coupled code; "God Class" and scattered functionality; prompt detail did not help; LOC predicts architectural smells (rho 0.94) [P, small sample, MetaGPT only].
- **Agentic refactoring** (arXiv 2511.04824, 2601.20160): agents refactor in 26% of commits but mostly small local edits (rename, retype), with small significant metric gains. Neither study verifies behaviour preservation [P abstract; full text not checked].
- **Not found:** any measured rate for agents deleting or weakening tests, or for over-defensive code beyond "broad exception handling" counts. Treat those as anecdotal.


## (G) Design implications for a Claude Code skill with reviewer subagents and a cleanup loop

**Stages**
0. **Scope and preflight.** Determine target (diff vs main, or a path list for whole-repo cleanup). Clean tree or a worktree. Record the baseline: tool results and test status. If tests are red at baseline, stop.
1. **Deterministic sweep.** Run section E commands, capture machine-readable output (`--format json`). Save as `tool-findings.json`. Autofix only formatter and safe ruff/eslint fixes, in a separate commit.
2. **Context pack.** Read AGENTS.md/CLAUDE.md and a `REVIEW.md`-style file (what counts as Block, nit cap, do-not-report list). Pass the pack to every subagent.
3. **Parallel finders (fresh contexts, disjoint lenses).** Suggested lenses: correctness and edge cases; security and data; error handling and observability; tests quality (assertions, mocks, weakened tests); simplicity/duplication/dead code (consumes knip/vulture/jscpd output as leads); consistency with repo conventions. Cheaper models for lenses that mostly triage tool output, the strongest model for correctness and security. Each finding must include file:line, a one-sentence claim, evidence (quoted code and the call path), a severity, and a proposed minimal fix. No evidence, no finding.
4. **Verification.** One independent verifier per finding, with a skeptical prompt: "try to refute it; cite the lines that prove or disprove." Where possible make verification executable: write and run a failing test or script (Codex does this; the overcorrection paper's fix-guided test is the same idea). Drop on refute or on "can't confirm." Verifiers should not see the finder's reasoning beyond the claim, to avoid anchoring.
5. **Dedupe and rank.** Merge by (file, line range, root cause) and by embedding or LLM similarity; keep the highest-evidence copy and record which lenses agreed (agreement across lenses is a confidence signal, as in Bugbot's voting). Rank: severity (Block > Fix > Nit), then confidence, then fix cost. Cap output (e.g. all Blocks, top 10 Fixes, 5 Nits plus a count). Pre-existing issues go in a separate "backlog" list, not the fix list.
6. **Human gate.** Present the ranked list; the user picks. Never auto-apply Block-level logic changes without approval; auto-applying low-risk cleanup (dead code proven unreferenced by two tools, formatting) is acceptable.
7. **Cleanup loop (per approved item).** In a worktree: add or confirm characterization test, apply one change, run typecheck, lint, tests, then diff review by a fresh agent that checks "behaviour unchanged, scope respected, no weakened tests, no new type escapes." Commit per item. On failure, revert that item and mark it "needs human."
8. **Re-verify.** Re-run the deterministic sweep and the tests; compare against the baseline (complexity, duplication, dead-code counts must not rise).

**Stop rules**
- Stop when a round yields no Block or Fix findings that survive verification, or after 2 review-fix rounds (diminishing returns; Anthropic's own docs describe a "round seven on style alone" failure and add a convergence rule: after the first review, only Important findings).
- After the first round, suppress nits.
- Hard caps: files touched, diff lines per item, total tokens or cost; abort when exceeded.
- Stop and ask on any red test that was green at baseline, any change to public interfaces, dependencies or test files, and any finding the verifier marks uncertain.
- Cleanup loop never runs more than N (e.g. 10) items per session; larger sets go to separate PRs.

**Other implications**
- Keep the review report short and evidence-first; use severity tags and a tally line.
- Record feedback (accepted, rejected, reason) in a file; promote repeated rejections to the do-not-report list. This is the cheap version of Greptile/Anthropic's 👍/👎 loop.
- Skip generated files, lockfiles and vendored code.
- Use the existing `/code-review` as a baseline lens rather than rebuilding it; add the lenses it lacks (tests quality, slop catalogue in C, conventions from AGENTS.md).
- Ship the catalogue in (C) as a checklist the simplicity and tests lenses must walk through.


## (H) Sources

Primary (read):
- Claude Code Review and `/code-review` docs: https://code.claude.com/docs/en/code-review (fetched 2026-10-12)
- anthropics/claude-code code-review plugin command: https://raw.githubusercontent.com/anthropics/claude-code/main/plugins/code-review/commands/code-review.md
- Cursor, "Building a better Bugbot": https://cursor.com/blog/building-bugbot (v11, Jan 2026)
- BitsAI-CR (ByteDance), Jan 2025: https://arxiv.org/html/2501.15134v1
- CR-Bench, Mar 2026: https://arxiv.org/abs/2603.11078
- AI-Generated Smells, May 2026: https://huggingface.co/papers/2605.02741
- Google eng-practices, what to look for: https://google.github.io/eng-practices/review/reviewer/looking-for.html
- Over-mocked tests, MSR 2026: https://arxiv.org/abs/2602.00409
- Agent PR post-merge quality: https://arxiv.org/abs/2601.20109
- Meta ACH, mutation-guided test generation: https://arxiv.org/html/2501.12862v1
- Google migrations with LLMs: https://arxiv.org/abs/2504.09691
- Meta MetaMateCR (FSE 2026 industry): https://conf.researchr.org/details/fse-2026/fse-2026-industry-papers/16/AI-Assisted-Fixes-to-Code-Review-Comments-at-Scale
- Agentic refactoring: https://arxiv.org/abs/2511.04824 and https://arxiv.org/abs/2601.20160
- LLM review overcorrection: https://arxiv.org/pdf/2603.00539 ; verification failures https://arxiv.org/html/2508.12358v1 ; HalluJudge https://arxiv.org/html/2601.19072v2
- Jules critic: https://developers.googleblog.com/meet-jules-sharpest-critic-and-most-valuable-ally/
- Copilot changelogs: https://github.blog/changelog/2026-03-05-copilot-code-review-now-runs-on-an-agentic-architecture/ and https://github.blog/changelog/2025-10-28-new-public-preview-features-in-copilot-code-review-ai-reviews-that-see-the-full-picture/
- Codex GitHub review docs: https://developers.openai.com/codex/integrations/github

Secondary or vendor (search snippets only, not fully read):
- Greptile v3: https://greptile.com/blog/greptile-v3-agentic-code-review
- Qodo 2.0: https://www.qodo.ai/blog/Introducing-qodo-2.0-agentic-code-review/
- Martian benchmark coverage: https://coderabbit.ai/blog/coderabbit-tops-martian-code-review-benchmark ; https://blog.kilo.ai/p/martians-independent-benchmark-tested
- Graphite false-positive guide: https://graphite.com/guides/ai-code-review-false-positives
- Amp review agent: https://hackernoon.com/amps-code-review-agent-tries-to-cut-the-low-signal-noise
- Liu et al. and Huang et al. summary: https://codex.danielvaughan.com/2026/06/23/silent-technical-debt-ai-generated-code-empirical-evidence-codex-cli-quality-defence-patterns/ (underlying arXiv 2603.28592, 2601.21276; not read directly)
- Tool versions: npm registry and PyPI JSON API, queried 2026-10-12.

Unverified or gaps: Anthropic's 16% to 54% and under-1% figures (from news write-ups, not in the docs page); Graphite sub-3% claim; Copilot linter/CodeQL ship date; Qodo F1; the exact Martian leaderboard (rankings conflict by vendor); any measurement of test-weakening or over-defensive code; whether the agentic refactoring studies check behaviour preservation; precision of the 0-100 confidence scoring (older plugin description vs current command file). Registry versions such as typescript 7.0.2 and eslint 10.12.0 are what the registries returned; check compatibility with the Expo SDK pin before upgrading.
