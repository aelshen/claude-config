# Usage Examples

Real-world examples demonstrating the agent workflow in action.

## Available Examples

### [Quick Bug Fix](./quick-bug-fix.md)
Simple workflow for fixing a small bug with reality checks and simplicity reviews.

**Time:** 2-3 minutes
**Agents:** oathkeeper, code-quality-pragmatist
**Best for:** Single-file bugs, small fixes

### [Feature Implementation](./feature-implementation.md)
Complete workflow for implementing a "forgot password" feature with comprehensive review.

**Time:** 5-7 minutes
**Agents:** workflow-orchestrator (coordinates multiple)
**Best for:** New features, multi-file changes

### [Debugging Production Issue](./debugging-workflow.md)
Deep debugging of mysterious intermittent 500 errors in production.

**Time:** 3-5 minutes
**Agents:** ultrathink-debugger, oathkeeper, code-quality-pragmatist
**Best for:** Mysterious bugs, production issues, edge cases

## Example Selection Guide

| Your Situation | Recommended Example |
|---------------|---------------------|
| Fixing a small bug | Quick Bug Fix |
| Adding a new feature | Feature Implementation |
| Mysterious production issue | Debugging Production Issue |
| Learning the basics | Quick Bug Fix → Feature Implementation |
| Understanding orchestrator | Feature Implementation |
| Understanding deep debugging | Debugging Production Issue |

## Common Patterns Across Examples

### Pattern 1: Reality Check First
Always verify implementations actually work before celebrating completion.

```
Implement → oathkeeper (verify) → Continue
```

### Pattern 2: Simplicity Review
Ensure solutions aren't over-engineered.

```
Fix applied → code-quality-pragmatist → Simplify if needed
```

### Pattern 3: Orchestrated Reviews
For complex work, let orchestrator coordinate multiple agents.

```
Major implementation → workflow-orchestrator → Address issues → Verify
```

### Pattern 4: Deep Debug → Verify
For mysterious bugs, debug deeply then verify the fix.

```
ultrathink-debugger (identify root cause) → Fix → oathkeeper (verify)
```

## Learning Path

1. **Start with Quick Bug Fix** - Understand basic agent usage
2. **Move to Feature Implementation** - Learn orchestrator workflow
3. **Try Debugging Example** - See deep debugging in action
4. **Apply to your own work** - Use patterns in real projects

## Contributing Examples

Have a great real-world usage story? Consider contributing!

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on submitting examples.
