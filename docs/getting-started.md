# Getting Started with AE Claude Code Setup

Quick start guide for using the custom agent workflow.

## Installation

### Option 1: Global Configuration
Copy `CLAUDE.md` to your home directory for use across all projects:

```bash
cp CLAUDE.md ~/.claude/CLAUDE.md
```

### Option 2: Per-Project Configuration
Copy `CLAUDE.md` to your project root:

```bash
cp CLAUDE.md /path/to/your/project/CLAUDE.md
```

## Your First Agent Invocation

Let's walk through a typical development workflow.

### Step 1: Implement a Feature

```
You: "Add a login endpoint with email/password validation"
Claude: [Implements the feature]
```

### Step 2: Reality Check

Before celebrating, verify it actually works:

```
You: "Use oathkeeper to validate this login implementation"
```

Oathkeeper will:
- Check if code compiles
- Verify tests pass
- Validate end-to-end functionality
- Identify any gaps

### Step 3: Simplicity Check

Ensure the implementation isn't over-engineered:

```
You: "Use code-quality-pragmatist to review for over-engineering"
```

This will catch:
- Unnecessary abstractions
- Premature optimization
- Over-complicated patterns

### Step 4: Update Progress

Track completion in your project:

```
You: "Use project-manager to update checklist"
```

## Common Workflows

### Quick Bug Fix Flow

```
1. Fix the bug
2. "Use oathkeeper to verify the fix works"
3. "Use code-quality-pragmatist to ensure fix is simple"
4. Done!
```

**Time:** 2-3 minutes of agent work

### Feature Implementation Flow

```
1. Implement the feature
2. "Use workflow-orchestrator to review the implementation"
   (This runs oathkeeper, project-manager, code-quality, and others)
3. Address any issues found
4. Done!
```

**Time:** 5-7 minutes of agent work

### Major Refactoring Flow

```
1. Plan the refactoring
2. Implement the changes
3. "Use workflow-orchestrator in comprehensive mode"
4. Verify all tests pass
5. Address issues
6. Done!
```

**Time:** 8-12 minutes of agent work

### Debugging Production Issues

```
1. Reproduce the issue
2. "Use ultrathink-debugger to investigate [description of issue]"
3. Implement recommended fix
4. "Use oathkeeper to verify fix works"
5. Deploy
```

**Time:** 3-5 minutes of agent work

## Decision Tree: Which Agent?

```
Are you implementing something new?
├─ Yes → After implementation, use workflow-orchestrator
└─ No
   │
   Is something broken/buggy?
   ├─ Yes
   │  └─ Is it mysterious or hard to reproduce?
   │     ├─ Yes → Use ultrathink-debugger
   │     └─ No → Fix it, then use oathkeeper to verify
   └─ No
      │
      Are you refactoring existing code?
      ├─ Yes → After changes, use code-quality-pragmatist
      └─ No
         │
         Do you need project status?
         └─ Yes → Use project-manager
```

## Tips for Success

1. **Don't skip oathkeeper** - It's tempting to assume code works, but reality checks save time
2. **Use workflow-orchestrator for big changes** - It coordinates everything automatically
3. **Direct agents for quick checks** - Faster than orchestrator for targeted reviews
4. **Fix critical issues first** - If oathkeeper finds breakage, fix before other reviews
5. **Iterate** - Re-run specific agents after fixes rather than full orchestration

## Understanding Agent Output

### Severity Levels

Agents use consistent severity levels:

- **Critical**: Blocks functionality, must fix immediately
- **High**: Significant issue, should fix before merge
- **Medium**: Should address, but not blocking
- **Low**: Nice to have, consider for future

### Example Output Format

```
## Critical Issues
- [file.ts:42] Authentication bypass vulnerability
  Fix: Add authorization check before data access

## High Priority
- [api.ts:120] Over-engineered abstraction layer
  Suggestion: Remove unnecessary UserRepositoryFactory

## Medium Priority
- [test.ts:50] Missing test coverage for edge case

## Strengths
- Clean separation of concerns in auth module
- Good error handling in validation layer
```

## Next Steps

- Read [agent-reference.md](./agent-reference.md) for detailed agent documentation
- Check [examples/](../examples/) for real-world usage scenarios
- Customize `CLAUDE.md` based on your workflow preferences
