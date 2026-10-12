# AE Claude Code Setup

A collection of custom Claude Code sub-agents and workflows for intelligent development assistance.

## Overview

This repository contains a structured approach to using Claude Code with custom sub-agents that provide specialized capabilities for common development tasks. The setup emphasizes pragmatic code quality, reality-checking implementations, and maintaining simplicity.

## Core Philosophy

- **Favor simplicity over theoretical best practices**
- **Question abstractions that don't deliver clear value**
- **Prefer working code over perfect architecture**
- **Balance pragmatism with maintainability**
- **Ship features, iterate on improvements**

## Installation

Requires `jq`. Clone the repo somewhere permanent, then run the installer:

```bash
git clone https://github.com/aelshen/claude-config ~/code/claude-config
~/code/claude-config/install.sh
```

It symlinks `CLAUDE.md`, `agents/`, `budget/` and `skills/` into `~/.claude`, so edits in either place are the same file. `settings.json` is merged into yours rather than linked, so machine-specific keys stay local; for the hook events this repo defines, its hook list replaces yours. Anything it replaces is moved to `~/.claude/backups/<timestamp>/` first. Re-running is safe.

For per-project use instead, copy `CLAUDE.md` into the project root.

## What's in the repo

| Path | What it is |
|------|------------|
| `CLAUDE.md` | Global instructions: git rules, model tiering, agent workflow, budget awareness |
| `agents/` | The sub-agents described below, each pinned to a model tier |
| `budget/` | Status line + hooks that show Claude its context use and plan limits |
| `skills/session-handoff/` | Writes resume notes; the budget rules call it |
| `settings.json` | Main model, subagent default model, status line and hooks |

## Model tiering

Opus plans, Sonnet builds, Haiku fetches. The main session is the expensive, smart layer; volume work goes down a tier.

| Tier | Runs | Agents |
|------|------|--------|
| Opus | Main session: planning, specs, review, final answers | main session, built-in `Plan`, `ultrathink-debugger` |
| Sonnet | One scoped task end to end; the default for any subagent | `implementer`, `general-purpose`, `oathkeeper`, `code-quality-pragmatist`, `project-manager`, `workflow-orchestrator` |
| Haiku | Search/retrieval at volume; small, fully specified edits | `Explore`, `fixer` |

How it's wired, all through documented Claude Code settings:

- `settings.json` sets `"model": "opus"` for the main session and `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`, the model for any subagent that doesn't name its own.
- Each file in `agents/` sets `model:` (and `effort:`) in its frontmatter, which beats the env default.
- `agents/Explore.md` overrides the built-in `Explore` agent. The built-in one runs on the main session's model (Opus); this one runs on Haiku at medium effort and skips CLAUDE.md, like the built-in.
- `CLAUDE.md` § Model Tiering tells the main session when to route to which agent, how to brief a lower tier, and when to escalate.

Precedence, highest first: a `model` passed on the Agent call → agent frontmatter → `CLAUDE_CODE_SUBAGENT_MODEL` → main session model. Aliases (`opus`, `sonnet`, `haiku`) track the latest release; to pin one, set `ANTHROPIC_DEFAULT_HAIKU_MODEL` (or `_SONNET_`/`_OPUS_`) in `env`.

To see where tokens actually go, run `budget/tier-report.sh [days]`: tokens and list-price cost per agent type and model, from your transcripts. Why the tiers are set this way, with sources: [docs/model-tiering.md](docs/model-tiering.md).

## Budget awareness

Claude can't see how full its context is or how much of the 5h/7d plan limit is left. The status line receives both from Claude Code, so `budget/statusline.sh` displays them and caches them per session in `~/.claude/state/budget/`. Hooks then read that cache:

- `inject.sh` (UserPromptSubmit) adds one `[budget]` line before every message. At 80% context it asks for handoff notes at the next break; at 85% it orders them now, then asks you to `/compact` or `/clear`. Plan limits: 80% says avoid subagents, 92% says stop and write resume notes.
- `agent-brake.sh` (PreToolUse on Agent/Workflow) asks before spawning subagents at 90% of a plan limit and refuses at 97%.
- `after-compact.sh` (SessionStart on compact/clear) points Claude back at its handoff notes.

Override thresholds with `CLAUDE_BUDGET_CTX_WARN`, `CLAUDE_BUDGET_CTX_ACT`, `CLAUDE_BUDGET_LIM_WARN`, `CLAUDE_BUDGET_LIM_ACT`, `CLAUDE_BUDGET_BRAKE_ASK`, `CLAUDE_BUDGET_BRAKE_DENY`.

Limits: plan-limit numbers only exist for claude.ai Pro/Max (or a gateway spend limit); other accounts see context only. Hooks can't trigger `/compact`, so Claude writes notes and asks you to run it.

## Available Custom Agents

### Explore (haiku)
Read-only search and retrieval: where things live, call sites, excerpts across many files, facts out of logs and docs. Every claim comes with `path:line`. Replaces the built-in `Explore`.

**Use when:** the answer means reading more than a few files. Run several in parallel for independent questions.

### fixer (haiku)
Applies a small change that's already decided: named files, the edit, the check. Stops and reports instead of guessing when the brief doesn't match the code or the change grows.

**Use when:** applying review findings, a rename, a known fix at a known line.

### implementer (sonnet)
Delivers one scoped task end to end from a spec: reads the area, implements, verifies against the acceptance check, reports decisions made.

**Use when:** a plan is broken into tasks; give each implementer disjoint files.

### workflow-orchestrator
Master coordinator for comprehensive quality assurance. Intelligently selects and coordinates multiple agents based on context.

**Use when:**
- After major implementation work
- Before key milestones (deployment, merge)
- When you need comprehensive quality checks

**Time:** 5-10 minutes

### oathkeeper
Reality-check agent that validates actual completion vs claimed completion. Ensures implementations actually work end-to-end.

**Use when:**
- You suspect tasks are marked complete but aren't functional
- Before marking major tasks as done
- After integrating complex components

**Time:** 1-2 minutes

### project-manager
Tracks progress, updates checklists, and verifies code compliance with project documentation.

**Use when:**
- After completing checklist items
- To get project status
- When code might deviate from documented patterns

**Time:** 1 minute

### code-quality-pragmatist
Reviews code for over-engineering, unnecessary complexity, and pragmatic quality issues.

**Use when:**
- After implementing abstractions or patterns
- When solution feels complex
- After refactoring

**Time:** 1-2 minutes

### ultrathink-debugger
Deep debugging specialist for complex issues, mysterious bugs, and production problems.

**Use when:**
- Bugs are mysterious or intermittent
- For production issues
- When initial debugging attempts fail

**Time:** 3-5 minutes

## Usage Guide

### Quick Reference

| Situation | Recommended Approach | Time | Agents |
|-----------|---------------------|------|---------|
| Small bug fix (<50 LOC) | Direct: oathkeeper + code-quality | 2-3 min | 2 |
| Feature implementation | Orchestrator: Standard Track | 5-7 min | 5-6 |
| Major feature/refactor | Orchestrator: Comprehensive | 8-12 min | 7-9 |
| Pre-deployment check | Orchestrator: Comprehensive | 8-12 min | 8-10 |
| Debugging complex issue | Direct: ultrathink-debugger | 3-5 min | 1 |
| Quick status check | Direct: project-manager | 1 min | 1 |

### Example Usage

**After implementing a new feature:**
```
"Use workflow-orchestrator to review the new authentication system"
```

**Quick reality check:**
```
"Use oathkeeper to validate this authentication implementation"
```

**Debugging production issue:**
```
"Use ultrathink-debugger to investigate these 500 errors"
```

**Check project status:**
```
"Use project-manager to update checklist and verify compliance"
```

**Review for over-engineering:**
```
"Use code-quality-pragmatist to review for over-engineering"
```

## Best Practices

1. **Start with Reality Check**: Always run oathkeeper before celebrating completion
2. **Don't Over-Orchestrate**: For quick changes, use direct agents instead of orchestrator
3. **Parallel Thinking**: Orchestrator runs compatible agents in parallel for speed
4. **Context Matters**: Orchestrator adapts to what you built (API vs UI vs Infrastructure)
5. **Fix Critical First**: If oathkeeper finds breakage, fix before running other reviews
6. **Iterate**: Re-run specific agents after fixing issues rather than full orchestration

## Future Enhancements

Planned automatic hooks (not yet implemented):

- **Post-Implementation Hook**: Auto-run oathkeeper + code-quality after >50 LOC changes
- **Pre-Commit Hook**: Auto-run project-manager for compliance checks
- **Pre-PR Hook**: Auto-run workflow-orchestrator in standard mode

**Current Workaround**: Manually invoke agents before commits/PRs

## Communication Preferences

- Be concise and direct
- Use bullet points for clarity
- Provide file:line references for code issues
- Prioritize Critical > High > Medium > Low
- Acknowledge strengths alongside improvements

## Contributing

This is a personal setup shared publicly. Feel free to fork and customize for your own needs.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines.

## License

MIT License - feel free to use and modify as needed.
