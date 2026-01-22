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

1. Copy `CLAUDE.md` to your project root or `~/.claude/CLAUDE.md` for global settings
2. Customize the configuration based on your preferences
3. Start using the agents through Claude Code

## Available Custom Agents

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
