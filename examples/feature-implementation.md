# Example: Feature Implementation Workflow

Real-world example of using the agent workflow to implement a new feature.

## Scenario

You need to add a "forgot password" feature to your web application.

## Step-by-Step Walkthrough

### 1. Initial Request

```
You: "I need to implement a forgot password feature. Users should be able to request a password reset link via email, and then set a new password using a secure token."
```

### 2. Claude Implements the Feature

Claude will:
- Create API endpoint for password reset request
- Generate secure reset tokens
- Send email with reset link
- Create endpoint to verify token and set new password
- Add necessary database migrations
- Write tests

### 3. Comprehensive Review

```
You: "Use workflow-orchestrator to review the forgot password implementation"
```

#### Orchestrator Execution

**Phase 1: Reality Check (oathkeeper)**
```
Running oathkeeper to verify implementation...

✓ Code compiles successfully
✓ All tests pass (12/12)
✓ Database migrations run successfully
✗ Email service not configured in test environment
  → Fix: Add mock email service for tests

Status: Implementation works but needs email mocking for tests
```

**Phase 2: Project Compliance (project-manager)**
```
Checking against project documentation...

✓ Follows existing API patterns in /api/auth/*
✓ Matches error handling conventions
✓ Updated checklist.md with completed items
✓ Consistent with CLAUDE.md security guidelines

Status: Compliant with project standards
```

**Phase 3: Simplicity Review (code-quality-pragmatist)**
```
Reviewing for over-engineering...

✗ High: Unnecessary TokenGeneratorFactory abstraction
  → Current: new TokenGeneratorFactory().create().generate()
  → Simpler: crypto.randomBytes(32).toString('hex')

✗ Medium: Over-complicated token validation logic
  → Could be simplified from 45 lines to ~15 lines

✓ Email service integration is appropriately simple
✓ Database schema is minimal and focused

Status: 2 over-engineering issues found
```

#### Synthesized Output

```
=== Comprehensive Review Summary ===

CRITICAL: None

HIGH PRIORITY:
1. [auth/tokens.ts:23] Remove TokenGeneratorFactory abstraction
   - Replace with direct crypto.randomBytes call
   - Reduces complexity from 3 files to inline implementation

2. [auth/validation.ts:67] Simplify token validation logic
   - Current implementation has nested conditionals
   - Can be flattened to guard clauses

MEDIUM PRIORITY:
3. [tests/auth.test.ts:120] Add mock email service
   - Tests currently skip email verification
   - Should mock and verify email content

STRENGTHS:
✓ Clear separation between reset request and password update
✓ Secure token generation with expiration
✓ Good error messages for user feedback
✓ Database schema is minimal and appropriate

RECOMMENDATION: Address items 1-2 before merge, item 3 can follow.
```

### 4. Address Feedback

```
You: "Fix the TokenGeneratorFactory and validation logic issues"
```

Claude makes the changes, simplifying the code.

### 5. Verify Fixes

```
You: "Use oathkeeper and code-quality-pragmatist to verify the fixes"
```

#### Oathkeeper Output
```
✓ Code still compiles
✓ All tests still pass (12/12)
✓ Simplified code maintains same functionality
✓ No regressions detected

Status: Fixes are solid
```

#### Code-Quality Output
```
✓ TokenGeneratorFactory removed, using crypto.randomBytes directly
✓ Validation logic simplified from 45 to 18 lines
✓ Code is now more maintainable and readable

Status: No over-engineering detected
```

### 6. Final Update

```
You: "Use project-manager to mark this complete"
```

#### Project Manager Output
```
Updated checklist.md:
- [x] Implement forgot password feature
  - [x] Password reset request endpoint
  - [x] Secure token generation
  - [x] Email integration
  - [x] Password update endpoint
  - [x] Tests and documentation

Status: Feature complete and ready for merge
```

## Key Takeaways

1. **workflow-orchestrator caught issues early** - Before code review, we found over-engineering
2. **oathkeeper verified functionality** - Ensured code actually works throughout changes
3. **code-quality-pragmatist kept it simple** - Prevented unnecessary abstractions from shipping
4. **project-manager tracked progress** - Checklist stays up to date automatically

## Time Breakdown

- Implementation by Claude: ~5 minutes
- Orchestrator review: ~6 minutes
- Fixing issues: ~2 minutes
- Verification: ~2 minutes
- **Total: ~15 minutes** (vs potential hours in code review cycle)

## Alternative: Without Orchestrator

For a simpler approach, you could run agents individually:

```
"Use oathkeeper to verify the forgot password feature works"
"Use code-quality-pragmatist to check for over-engineering"
"Use project-manager to update the checklist"
```

This gives you more control but requires manual coordination.
