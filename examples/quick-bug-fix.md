# Example: Quick Bug Fix Workflow

Simple example showing the streamlined workflow for fixing a small bug.

## Scenario

A user reports that the logout button doesn't clear the session token, allowing continued access after logout.

## Traditional Approach (Without Agents)

1. Fix the bug (~5 min)
2. Manually test (~5 min)
3. Commit and push
4. Code review catches that fix is over-complicated (~1 day)
5. Revise and re-test (~10 min)
6. Re-review and merge (~1 day)

**Total: ~2 days elapsed, 20 minutes of work**

## Streamlined Approach (With Agents)

### 1. Implement the Fix

```
You: "The logout function isn't clearing the session token. Fix it."
```

Claude fixes the issue:

```typescript
// Before
async logout() {
  await this.authService.invalidateSession()
  // Missing: clear client-side token
}

// After
async logout() {
  await this.authService.invalidateSession()
  localStorage.removeItem('auth_token')
  this.currentUser = null
}
```

### 2. Reality Check

```
You: "Use oathkeeper to verify the logout fix works"
```

#### Oathkeeper Output (30 seconds)

```
Testing logout functionality...

✓ Session invalidated on server
✓ Token cleared from localStorage
✓ User state reset to null
✓ Attempting to use old token: properly rejected
✓ All tests pass (5/5)

Status: Fix works correctly
```

### 3. Simplicity Check

```
You: "Use code-quality-pragmatist to review the fix"
```

#### Code-Quality Output (45 seconds)

```
Reviewing logout fix...

✗ Medium: Over-complicated implementation

Current approach:
1. Call authService.invalidateSession() (async)
2. Clear localStorage
3. Reset currentUser

Issues:
- invalidateSession() makes API call but doesn't wait for response
- If API call fails, client state still clears (user thinks they're logged out)
- Race condition potential

Simpler and more correct:
await this.authService.invalidateSession()
  .finally(() => {
    localStorage.removeItem('auth_token')
    this.currentUser = null
  })

This ensures client clears state whether API succeeds or fails.

Status: Found simplification opportunity
```

### 4. Apply Suggestion

```
You: "Apply the suggested fix using .finally()"
```

Claude updates:

```typescript
async logout() {
  await this.authService.invalidateSession()
    .finally(() => {
      localStorage.removeItem('auth_token')
      this.currentUser = null
    })
}
```

### 5. Final Verification

```
You: "Use oathkeeper to verify the updated fix"
```

#### Oathkeeper Output (30 seconds)

```
Re-testing logout functionality...

✓ Session invalidated on server
✓ Token cleared even if API fails (tested)
✓ User state reset correctly
✓ All tests pass including error cases (7/7)

Status: Fix is now robust and correct
```

### 6. Done!

```
You: "Commit this fix"
```

Claude commits with appropriate message. Ready for merge.

## Results Comparison

| Aspect | Traditional | With Agents |
|--------|------------|-------------|
| Implementation | 5 min | 5 min |
| Testing | 5 min manual | 1 min automated |
| Code review | 1-2 days | 2 min |
| Revision | 10 min | 2 min |
| Re-review | 1 day | 1 min |
| **Total elapsed** | **~2 days** | **~11 minutes** |
| **Quality** | Eventually good | Good immediately |

## Key Benefits

1. **Immediate feedback** - No waiting for code review cycle
2. **Higher quality** - Caught the race condition before it shipped
3. **Learning** - Explanation helps you understand the better approach
4. **Confidence** - Verified the fix actually works

## When to Use This Workflow

Perfect for:
- Single file changes
- Bug fixes
- Small refactorings
- Quick improvements

**Time:** 2-3 minutes of agent work

## Alternative: Even Faster

For very simple fixes where you're confident, you can combine:

```
You: "Fix the logout bug. Then use oathkeeper and code-quality-pragmatist to verify."
```

Claude will:
1. Implement fix
2. Run both agents automatically
3. Apply any suggestions
4. Give you the final result

**Time:** ~2 minutes total
