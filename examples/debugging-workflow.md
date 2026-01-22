# Example: Debugging Production Issue

Real-world example of using ultrathink-debugger to solve a mysterious production bug.

## Scenario

Users are reporting 500 errors on checkout, but only for certain items and only sometimes. Local testing doesn't reproduce the issue.

## Step-by-Step Walkthrough

### 1. Initial Report

```
You: "Users are getting 500 errors during checkout for certain items.
Happens intermittently - about 10% of transactions.
Can't reproduce locally.
Here are the error logs: [paste logs]"
```

### 2. Engage Deep Debugging

```
You: "Use ultrathink-debugger to investigate these checkout 500 errors"
```

### 3. Ultrathink-Debugger Analysis

#### Phase 1: Error Pattern Analysis

```
Analyzing error logs...

Pattern detected:
- All failures occur with items priced $X.99 (e.g., $19.99, $49.99)
- Failures only happen with discount codes applied
- Error occurs in payment processing service
- Stack trace shows: "Invalid amount: -0.009999999999999998"

Initial hypothesis: Floating point precision issue in discount calculation
```

#### Phase 2: Code Investigation

```
Tracing execution path...

File: services/checkout.ts:156
  finalAmount = itemPrice * (1 - discountPercent)

Issue identified:
1. itemPrice is stored as number (JavaScript float)
2. discountPercent is stored as number (e.g., 0.15 for 15%)
3. Calculation: 49.99 * (1 - 0.15) = 42.491500000000005
4. This rounds to 42.49 for display
5. But backend validation checks: sent_amount === calculated_amount
6. Mismatch due to floating point precision

Root cause: Floating point arithmetic without proper rounding
```

#### Phase 3: Environment Analysis

```
Why only in production?

Local environment:
- Uses test payment gateway
- Mock validation (less strict)
- Test data has round numbers

Production environment:
- Real payment gateway
- Strict amount validation to prevent fraud
- Real prices ending in .99

This explains why local testing didn't reproduce the issue.
```

#### Phase 4: Recommended Fix

```
Recommendation:

BAD (naive fix):
  finalAmount = Math.round(itemPrice * (1 - discountPercent) * 100) / 100
  Problem: Still using floating point arithmetic

GOOD (proper fix):
  // Use integer arithmetic (cents)
  const priceInCents = Math.round(itemPrice * 100)
  const discountInCents = Math.round(priceInCents * discountPercent)
  const finalInCents = priceInCents - discountInCents
  const finalAmount = finalInCents / 100

BEST (library):
  import { Decimal } from 'decimal.js'
  const finalAmount = new Decimal(itemPrice)
    .times(new Decimal(1).minus(discountPercent))
    .toDecimalPlaces(2)
    .toNumber()

Recommendation: Use Decimal.js for financial calculations
```

### 4. Implement the Fix

```
You: "Implement the Decimal.js solution for all financial calculations"
```

Claude implements:
- Add decimal.js dependency
- Update checkout.ts to use Decimal for all money calculations
- Update tax calculations
- Update discount calculations
- Add tests for edge cases (.99 prices, multiple discounts, etc.)

### 5. Verify the Fix

```
You: "Use oathkeeper to verify this fix resolves the floating point issue"
```

#### Oathkeeper Output

```
Testing fix against reported scenarios...

✓ Item at $49.99 with 15% discount: $42.49 (exact)
✓ Item at $19.99 with 10% discount: $17.99 (exact)
✓ Item at $99.99 with 20% discount: $79.99 (exact)
✓ All test cases pass (48/48)
✓ No floating point precision errors detected

Manual verification:
✓ Staging environment: 1000 synthetic transactions, 0 failures
✓ Backend validation: all amounts match exactly

Status: Fix resolves the issue completely
```

### 6. Additional Checks

```
You: "Use code-quality-pragmatist to ensure the fix isn't over-engineered"
```

#### Code-Quality Output

```
Reviewing Decimal.js implementation...

✓ Appropriate use of library for financial calculations
✓ Not over-engineered - Decimal.js is industry standard for this
✓ Centralized in money utility module (good)
✓ Tests cover edge cases without being excessive

Note: Using integer cents arithmetic would be slightly simpler,
but Decimal.js provides better clarity and handles more edge cases.
For financial calculations, this is the right choice.

Status: Implementation is pragmatic and appropriate
```

### 7. Document and Deploy

```
You: "Use project-manager to document this fix"
```

#### Project Manager Output

```
Updated documentation:

Added to docs/architecture.md:
- Financial calculations MUST use Decimal.js
- Never use native JavaScript floats for money
- All prices stored as Decimal, converted to number only for display

Updated checklist.md:
- [x] Fix checkout 500 errors
  - Root cause: Floating point precision
  - Solution: Decimal.js for financial math
  - Verified in staging with 1000 transactions

Created incident post-mortem:
- docs/incidents/2024-01-15-checkout-500-errors.md

Status: Documented and ready for deploy
```

## Outcome

**Problem:** Mysterious intermittent 500 errors in production
**Root Cause:** Floating point precision in discount calculations
**Solution:** Decimal.js for all financial arithmetic
**Time to Resolution:** ~15 minutes (vs hours/days of manual debugging)

## Key Insights from ultrathink-debugger

1. **Pattern Recognition**: Identified the .99 price correlation
2. **Environment Analysis**: Explained why local testing didn't reproduce
3. **Root Cause**: Floating point arithmetic, not business logic
4. **Proper Fix**: Recommended industry-standard solution (Decimal.js)
5. **Verification**: Confirmed fix works before deploy

## Lessons Learned

- **ultrathink-debugger excels at mysterious bugs** - Especially environment-specific issues
- **oathkeeper verified the fix** - Ensured solution actually works
- **code-quality-pragmatist validated approach** - Confirmed library choice was appropriate
- **project-manager documented learnings** - Prevents future recurrence

## Time Breakdown

- ultrathink-debugger investigation: ~4 minutes
- Implement fix: ~3 minutes
- Verification with oathkeeper: ~1 minute
- Code quality review: ~1 minute
- Documentation: ~1 minute
- **Total: ~10 minutes** (vs potentially days of trial-and-error)
