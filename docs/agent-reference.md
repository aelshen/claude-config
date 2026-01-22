# Agent Reference Guide

Detailed documentation for each custom agent in the AE Claude Code setup.

## workflow-orchestrator

### Purpose
Master coordinator that intelligently selects and runs multiple agents based on the type of work completed. Provides comprehensive quality assurance by orchestrating other agents in optimal sequence.

### When to Use
- After implementing features >100 LOC
- Before deployment or merging to main
- When you need multi-dimensional code review
- For comprehensive pre-release checks

### What It Does
1. Analyzes the context of recent changes
2. Determines which agents are relevant
3. Runs agents in optimal order (sequential for dependencies, parallel for independence)
4. Synthesizes results into actionable feedback
5. Prioritizes issues by severity

### Typical Workflow
```
oathkeeper (verify it works)
  → project-manager (check compliance)
  → Parallel:
      - code-quality-pragmatist
      - [other relevant agents based on context]
  → Final synthesis
```

### Expected Output
- Summary of all issues found
- Prioritized action items
- Verification that implementation actually works
- Recommendations for improvements

### Example Invocation
```
"Use workflow-orchestrator to review the new user authentication system"
```

---

## oathkeeper

### Purpose
Reality-check agent that cuts through incomplete implementations and validates actual completion vs claimed completion. Ensures code actually works end-to-end.

### When to Use
- You suspect tasks are marked complete but aren't functional
- Before marking major tasks as done
- After integrating complex components
- To validate that tests pass and functionality works

### What It Does
1. Assesses the actual state of implementation
2. Tests claims against reality (does it compile? do tests pass? does it run?)
3. Identifies gaps between claimed and actual completion
4. Creates realistic plans to finish remaining work

### Philosophy
No-bullshit assessment of what's actually been built vs what was claimed. Prevents false completion claims.

### Expected Output
- Reality check: What actually works vs what was claimed
- List of incomplete items that need attention
- Verification of end-to-end functionality
- Concrete next steps to achieve real completion

### Example Invocation
```
"Use oathkeeper to validate this authentication implementation"
```

---

## project-manager

### Purpose
Tracks project progress, updates checklists, and verifies that code changes align with project documentation and specifications.

### When to Use
- After completing checklist items
- To get project status updates
- When code might deviate from documented patterns (CLAUDE.md, specs)
- For design deviation detection
- Before status meetings

### What It Does
1. Reviews code changes against project documentation
2. Updates checklist.md with completed items
3. Flags inconsistencies between implementation and specs
4. Generates progress summaries
5. Ensures patterns match established conventions

### Expected Output
- Updated checklist.md with progress
- Compliance report (does implementation match specs?)
- List of deviations that need resolution
- Project status summary

### Example Invocation
```
"Use project-manager to update checklist and verify compliance"
```

---

## code-quality-pragmatist

### Purpose
Reviews code for over-engineering, unnecessary complexity, and common anti-patterns that lead to poor developer experience.

### When to Use
- After implementing abstractions or patterns
- When solution feels complex
- After refactoring
- To ensure code stays simple and pragmatic

### What It Does
1. Identifies over-engineering patterns
2. Questions unnecessary abstractions
3. Flags premature optimization
4. Ensures code matches project scale
5. Validates that complexity is justified

### Philosophy
Code should be as simple as possible for the task at hand. Abstractions should provide clear, immediate value. Avoid complexity for theoretical future needs.

### Expected Output
- List of over-engineering patterns found
- Suggestions for simplification
- Validation that abstractions are appropriate for project scale
- Pragmatic alternatives to complex implementations

### Example Invocation
```
"Use code-quality-pragmatist to review for over-engineering"
```

---

## ultrathink-debugger

### Purpose
Deep debugging specialist for complex issues, mysterious bugs, production problems, and edge cases that require root cause analysis.

### When to Use
- Bugs are mysterious or intermittent
- For production issues
- When initial debugging attempts fail
- Environment-specific failures
- Race conditions or timing issues

### What It Does
1. Performs systematic root cause analysis
2. Traces execution paths
3. Identifies subtle bugs and edge cases
4. Implements robust fixes
5. Ensures fixes don't introduce new problems

### Expected Output
- Root cause analysis
- Detailed explanation of the bug
- Robust fix implementation
- Verification that fix resolves the issue
- Recommendations to prevent similar bugs

### Example Invocation
```
"Use ultrathink-debugger to investigate these 500 errors"
```

---

## Combining Agents

### Typical Workflows

**Small Bug Fix:**
```
oathkeeper → code-quality-pragmatist
(Verify fix works, ensure no over-engineering)
```

**Feature Implementation:**
```
workflow-orchestrator
  → oathkeeper (does it work?)
  → project-manager (update checklist)
  → code-quality-pragmatist (keep it simple)
```

**Major Refactoring:**
```
workflow-orchestrator
  → oathkeeper (does everything still work?)
  → project-manager (matches specs?)
  → code-quality-pragmatist (actually simpler?)
```

**Production Debugging:**
```
ultrathink-debugger
  → oathkeeper (verify fix works)
  → code-quality-pragmatist (fix isn't over-engineered)
```
