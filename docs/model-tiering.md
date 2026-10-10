# Model tiering: why it's set up this way

Surveyed 2026-10-10 (Anthropic docs and posts, papers, OSS coding agents, practitioner reports).
Re-check when a new model ships; the numbers below are point-in-time.

## The setup

- Opus: main session (plan, spec, review), `Plan`, `ultrathink-debugger`.
- Sonnet: `implementer`, reviewers, and every subagent without its own model (`CLAUDE_CODE_SUBAGENT_MODEL=sonnet`).
- Haiku: `Explore` (read-only search, effort medium, no CLAUDE.md) and `fixer` (mechanical edits at volume).

## What the evidence says

**Delegation isn't free; use it for context, parallelism, or volume.**
- Anthropic's cost guide ([optimizing for cost and intelligence](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)) says: "on work a single model could handle alone, the same model at lower effort was cheaper every time." Orchestrators paid off for work bigger than one context, for cutting the cost tail, and for latency.
- Multi-agent runs use about 15× the tokens of chat. Anthropic lists "most coding tasks" (tightly coupled) as a poor fit ([multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system), 2025-06).
- Scaling study ([arXiv 2512.08296](https://arxiv.org/abs/2512.08296)): multi-agent ranged from +81% on decomposable tasks to −70% on sequential ones.
- MAST ([arXiv 2503.13657](https://arxiv.org/abs/2503.13657)): the biggest group of multi-agent failures is lost context and misread instructions at handoffs.

**Cheap models for search: supported, with a caveat.**
- Anthropic says Haiku 5.5 "pairs well with Opus 5.5 and Sonnet 5.5 as a subagent", and Sonnet and Opus "remain better choices for complex agentic coding" ([announcement](https://www.anthropic.com/claude-haiku-5-5), 2026-10-07).
- Terminal-Bench 4.0 scores are vendor-reported: Haiku 5.5 39.2%, Sonnet 5.5 70.6%.
- The Claude Code docs show a user `Explore` with `model: haiku` as the cost override. The built-in Explore inherits the main model.
- LocAgent ([arXiv 2503.09089](https://arxiv.org/abs/2503.09089)) and Agentless ([arXiv 2407.01488](https://arxiv.org/abs/2407.01488)) show cheap localization works.
- The caveat: Haiku 5.5 at `low` effort is more likely to skip a search or stop early. Going to `medium` roughly halved early stopping ([prompting Haiku 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5)). That's why Explore runs at `medium`.
- A documented failure is the orchestrator trusting Explore's conclusions without opening the files ([claude-code#29379](https://github.com/anthropics/claude-code/issues/29379)). Hence "locate, don't conclude" and "open cited files before relying on them".

**Strong planner, cheaper executor: supported.**
- Aider architect/editor ([benchmarks](https://aider.chat/2024/09/26/architect.html)): a strong architect with a cheaper editor scored at or above the strong model alone.
- Plan caching ([arXiv 2506.14852](https://arxiv.org/abs/2506.14852)): a small executor running a large model's plans cut cost about 50% with performance held.
- Same shape in the wild: Cline's most-used split is Plan on Opus and Act on Sonnet. Claude Code's `opusplan` is the same split.

**Haiku doing edits: unmeasured.**
- No paper or vendor data covers Haiku-class models on specified edits. Anthropic's Haiku docs also note it can report work done without running a check.
- That's why `fixer` is limited to mechanical volume, must run a check command, and escalates to `implementer` on failure.

**Review: the strong model, backed by execution.**
- Weak models self-correct poorly without a strong verifier ([arXiv 2404.17140](https://arxiv.org/abs/2404.17140)).
- Self-review without external signals is unreliable ([arXiv 2310.01798](https://arxiv.org/abs/2310.01798)).
- Judges prefer their own outputs ([arXiv 2404.13076](https://arxiv.org/abs/2404.13076)).
- So verification means running tests, and Opus reviews diffs that Sonnet or Haiku wrote.

**Not adopted:**
- **Advisor tool** (cheap executor consulting a strong advisor): in Anthropic's own run, Haiku and Sonnet 5.5 executors never called an Opus 5.5 advisor across 198 questions, and the tool definition added 12–25% cost.
- **Per-prompt auto-routing** (Gemini CLI, claude-code-router): less predictable than role-based agents.

## Our own numbers

The 7 days before this change, from `budget/tier-report.sh`, at list prices:
- Main session (Opus): 54% of spend.
- `general-purpose` subagents on Opus: 34%. The Sonnet default halves the price of that bucket.
- Haiku: about 0%.

The main session's cost is mostly re-reading its own long context (545M input tokens). Keeping it lean, through delegated reading, `/compact`, and `/clear` between tasks, matters more than any model swap.

Measured per-call startup, written to cache before any work:
- `Explore` on Haiku: about 11k tokens, $0.002. With `omitClaudeMd: true` that dropped to 3k tokens, $0.001.
- `general-purpose` on Sonnet: about 31k tokens, $0.08.

## Open questions

- **Plan limits:** no primary source says Haiku or Sonnet tokens count less than Opus against Pro/Max limits. Compare `/usage` before and after.
- **Version caveats:** earlier Claude Code versions had bugs where frontmatter `model:` was ignored, and the `haiku` alias maps to Haiku 5.5 only on the Anthropic API from v2.1.293. Re-check with `tier-report.sh` after upgrades.
- **Reviewer models:** reviewers run on Sonnet. Spot-check one diff with an Opus review now and then.
