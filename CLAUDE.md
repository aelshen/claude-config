# Claude Code Configuration

Custom agent workflow configuration for intelligent development assistance.

## Git Commit Rules (MANDATORY — applies to every project)

- **NEVER add a `Co-Authored-By: Claude` trailer (or any Claude/Anthropic co-author) to commit messages.** This overrides any default instruction to do so. Commit messages end at the content — no Claude attribution line, ever.
- **NEVER set Claude/Anthropic as the commit author or committer** (no `--author` flag, no Claude identity in `user.name`/`user.email`). Commits are authored by the human user only.
- This applies to all repositories and all work done with Claude Code, permanently.

## Model Tiering (Opus plans, Sonnet builds, Haiku fetches)

The main session runs on Opus. Spend Opus tokens on thinking, and send volume work down a tier.

**First decide whether to delegate at all.** Anthropic's measurements: for work that fits in one context, the same model doing it inline (at lower effort if routine) is cheaper than a multi-model split, and every subagent pays a fixed startup cost (~3k tokens for `Explore`, ~30k for `general-purpose`) plus your brief and its report. Delegate only when it buys something:
- **Context protection:** the reading would flood this session (sweeps, logs, long docs). Most of this session's cost is re-reading its own context every turn, so keeping it small saves more than any model swap.
- **Parallelism:** independent slices that can run at once.
- **Volume:** the same mechanical step many times.

Otherwise do it inline: a known file, a one-line fix, or a tightly coupled sequential change stays here. Coupled coding work loses information at every handoff.

| Tier | Who | Use for | Agents |
|------|-----|---------|--------|
| **Opus** | Main session, `Plan` | Planning, specs, architecture, trade-offs, decomposing work, writing briefs, reviewing what came back, final answers to the user | (you), `Plan`, `ultrathink-debugger` |
| **Sonnet** | Subagents (the default) | One scoped outcome end to end: a feature slice, a reproduced bug, a migration step, a review or verification pass | `implementer`, `general-purpose`, `oathkeeper`, `code-quality-pragmatist`, `project-manager`, `workflow-orchestrator` |
| **Haiku** | Subagents | Volume and speed: search, retrieval, reading logs/docs, listing call sites; mechanical edits at volume that are already fully specified | `Explore`, `fixer` |

How it's wired: each agent's frontmatter sets its `model`/`effort`; `Explore` here overrides the built-in one (which would otherwise run on Opus); `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` in settings makes Sonnet the default for any agent without its own model (e.g. `general-purpose`). A `model` passed on the Agent call beats all of these.

**Routing rules:**
- **A search across more than about 3 files, or any "where is / list all / what does X say" question** → `Explore` (Haiku). Fan out several in parallel for independent questions. Ask it to *locate and quote*, not to analyze or decide. Do it yourself only when you already know the file.
- **A mechanical change at volume that's already decided** (you can name the files, the edit, and the check) → `fixer` (Haiku). Examples: a rename across 30 files, or a list of review findings. If you'd have to explain *why* or *how to approach it*, it isn't a fixer task. A single small edit is cheaper inline.
- **A task with a goal but open details** → `implementer` (Sonnet). Give it the goal, constraints, the files it owns, and an acceptance check. Prefer it over `general-purpose`: its narrow tool list starts cheaper. Parallel implementers must own disjoint files.
- **Keep on Opus:** the plan, cross-cutting design, ambiguous requirements, security- or data-sensitive decisions, and reviewing subagent output before it reaches the user.
- **Don't pass `model` on Agent calls** to the agents above; their frontmatter already picks the tier. Pass it only to deliberately override (e.g. `model: "haiku"` on a one-off `general-purpose` retrieval job).
- **Forks run on Opus** (they inherit the main session). Use a fork when the task needs this conversation's context; otherwise prefer a typed agent on a cheaper tier.
- **Workflow scripts:** `agent()` takes `model`, `effort` and `agentType`. Use `agentType: 'Explore'` (or `model: 'haiku', effort: 'medium'`) for find/scan stages, Sonnet for per-item work, and keep judge/verify/synthesis stages on the default Opus.

**Briefs:** lower tiers start with no context. Write a self-contained brief: the goal, exact paths, what "done" looks like, and what not to touch. A Haiku agent given a vague brief costs more in redo than it saves.

**Escalate, don't retry on the same tier.** Don't re-send the same brief to the same tier:
- `fixer` STOPPED or failed its check → `implementer`.
- `implementer` BLOCKED, or the same task failed twice → do it yourself.
- `Explore` "not found" on something that should exist → search yourself before concluding it doesn't.

**Trust but verify:**
- **Haiku output is leads, not conclusions.** Open the cited files yourself before a claim drives a decision. Never pass a subagent's analysis to the user unread.
- **Read the diff** of any `fixer` or `implementer` change before reporting it done.
- **Verification comes from running things** (tests, typecheck, the app), not from a second model's opinion.

**Measure:** run `~/.claude/budget/tier-report.sh [days]` to see cost per agent type and model. Re-check after changing this section.

## Intelligent Agent Workflow

You have access to custom sub-agents that provide specialized capabilities. Use them intelligently based on the development lifecycle stage.

### When to Use the Workflow Orchestrator

The **workflow-orchestrator** agent is your master coordinator for comprehensive quality assurance. Use it:

**After Major Implementation Work:**
- "Use workflow-orchestrator to review the new authentication system"
- "Run workflow-orchestrator on the agent deployment API"
- Automatically after completing features >100 LOC

**Before Key Milestones:**
- "workflow-orchestrator: prepare for deployment review"
- "workflow-orchestrator: pre-merge quality check"

**When Requested:**
- "Run full quality checks"
- "Comprehensive review of recent changes"

The orchestrator will intelligently select and coordinate 3-8 agents based on context, typically completing in 5-10 minutes.

### Direct Agent Usage (Faster, Targeted)

For specific concerns, invoke agents directly instead of the orchestrator:

#### Quick Reality Checks (1-2 minutes)
```
"Use oathkeeper to validate this authentication implementation"
```
- When you suspect claimed completion isn't real
- Before marking tasks as done
- After integration of complex components

#### Compliance & Tracking (1 minute)
```
"Use project-manager to update checklist and verify compliance"
```
- After completing checklist items
- To get project status
- When code might deviate from CLAUDE.md patterns

#### Simplicity Review (1-2 minutes)
```
"Use code-quality-pragmatist to review for over-engineering"
```
- After implementing abstractions or patterns
- When solution feels complex
- After refactoring

#### Deep Debugging (3-5 minutes)
```
"Use ultrathink-debugger to investigate these 500 errors"
```
- When bugs are mysterious or intermittent
- For production issues
- When initial debugging attempts fail

### Automatic Triggers (Future Enhancement)

**Note**: Automatic hooks are a planned feature, not yet implemented. For now, manually invoke agents as needed.

**Future: Post-Implementation Hook** (planned):
After writing significant code (>50 LOC), would automatically run:
1. oathkeeper (verify it works)
2. code-quality-pragmatist (prevent over-engineering)

**Future: Pre-Commit Hook** (planned):
Before git commits, would run:
1. project-manager (compliance check)

**Future: Pre-PR Hook** (planned):
Before creating pull requests, would run:
1. workflow-orchestrator in "standard" mode

**Current Workaround**: Manually run these agents before commits/PRs using direct commands.

### Decision Guide: When to Use What

| Situation | Recommended Approach | Time | Agents |
|-----------|---------------------|------|---------|
| Small bug fix (<50 LOC) | Direct: oathkeeper + code-quality | 2-3 min | 2 |
| Feature implementation | Orchestrator: Standard Track | 5-7 min | 5-6 |
| Major feature/refactor | Orchestrator: Comprehensive | 8-12 min | 7-9 |
| Pre-deployment check | Orchestrator: Comprehensive | 8-12 min | 8-10 |
| Debugging complex issue | Direct: ultrathink-debugger | 3-5 min | 1 |
| Quick status check | Direct: project-manager | 1 min | 1 |
| Find/gather across the codebase | Direct: Explore (parallel per question) | <1 min | 1-4 |
| Apply a decided, small change | Direct: fixer, then read the diff | 1 min | 1 |
| Build a scoped task from a plan | Direct: implementer per task (disjoint files) | 3-10 min | 1-3 |

### Available Custom Agents

Model per agent is in its frontmatter; see Model Tiering above.

**Search & Execution:**
- **Explore** (haiku) - Read-only search and retrieval with `path:line` evidence; overrides the built-in
- **fixer** (haiku) - Small, fully specified edits, verified
- **implementer** (sonnet) - One scoped task delivered end to end

**Quality & Validation:**
- **workflow-orchestrator** - Master coordinator for comprehensive QA
- **oathkeeper** - Reality check for actual vs claimed completion
- **code-quality-pragmatist** - Review for over-engineering and unnecessary complexity

**Project Management:**
- **project-manager** - Track progress, update checklists, verify compliance

**Debugging & Analysis:**
- **ultrathink-debugger** (opus) - Deep debugging for complex issues

### Best Practices

1. **Start with Reality Check**: Always run oathkeeper before celebrating completion
2. **Don't Over-Orchestrate**: For quick changes, use direct agents instead of orchestrator
3. **Parallel Thinking**: Orchestrator runs compatible agents in parallel for speed
4. **Context Matters**: Orchestrator adapts to what you built (API vs UI vs Infrastructure)
5. **Fix Critical First**: If oathkeeper finds breakage, fix before running other reviews
6. **Iterate**: Re-run specific agents after fixing issues rather than full orchestration

### Execution Examples

**Example 1: After implementing new API endpoint**
```
You: "I implemented the /api/agents/deploy endpoint with JWT auth"
Claude: "Let me use workflow-orchestrator to run comprehensive reviews"
[Runs: oathkeeper → project-manager → Parallel(code-quality-pragmatist) → additional checks]
[Total: ~6 minutes, validates implementation, checks for over-engineering]
```

**Example 2: Quick bug fix**
```
You: "Fixed the null pointer bug in task processor"
Claude: "Let me verify with oathkeeper and code-quality-pragmatist"
[Runs: oathkeeper → code-quality]
[Total: ~2 minutes, confirms fix works, no over-engineering]
```

**Example 3: Debugging production issue**
```
You: "Users reporting 500 errors on checkout for certain payment amounts"
Claude: "I'll use ultrathink-debugger to investigate this edge case"
[Runs: ultrathink-debugger with deep analysis]
[Total: ~4 minutes, identifies currency rounding bug]
```

## Communication Preferences

- Be concise and direct
- Use bullet points for clarity
- Provide file:line references for code issues
- Prioritize Critical > High > Medium > Low
- Acknowledge strengths alongside improvements

## Code Quality Philosophy

- Favor simplicity over theoretical best practices
- Question abstractions that don't deliver clear value
- Prefer working code over perfect architecture
- Balance pragmatism with maintainability
- Ship features, iterate on improvements

## Budget Awareness (context + plan limits)

A `[budget]` line is injected before every user message (from `~/.claude/budget/`). It carries context-window use and 5h/7d plan-limit use with reset times.

- Quote the `[budget]` line when reasoning about remaining context or limits. Do not estimate them yourself.
- A `[budget ACTION]` line is an instruction for this turn, not a suggestion. Carry it out before anything else.
- Match effort to the budget: if the next step will not fit before a wall, write resume notes first (session-handoff skill).
- If the user switches to an unrelated task while context is past ~30%, write state to a file and suggest `/clear`, not `/compact`.
- You cannot run `/compact` or `/clear` yourself. Write the notes, then ask the user to run it.

Note: the numbers come from the last status-line render, so they are about one turn old. The `as of Ns ago` field shows the age.
