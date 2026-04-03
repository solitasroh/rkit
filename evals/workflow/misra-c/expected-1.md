## MISRA C:2012 Violation Analysis Report

### Violation 1: Uninitialized Variable

- **Rule**: R.9.1 - The value of an object with automatic storage duration shall not
  be read before it has been set
- **Severity**: Required
- **Location**: Line 6 - `int result;` used at return without guaranteed initialization
- **Issue**: If `count` is 0, `result` is returned without being assigned
- **Fix**: Initialize at declaration: `int result = 0;`

### Violation 2: Assignment in Condition Expression

- **Rule**: R.14.3 - Controlling expressions shall not be invariant /
  R.13.4 - The result of an assignment operator shall not be used
- **Severity**: Required
- **Location**: Line 11 - `if (readings[i] = 0)`
- **Issue**: Assignment operator `=` used instead of comparison `==`
- **Fix**: Change to `if (readings[i] == 0)`

### Violation 3: Use of Banned Library Function (printf)

- **Rule**: R.21.6 - The Standard Library input/output functions shall not be used
- **Severity**: Required
- **Location**: Line 13 - `printf("Zero reading at index %d\n", i);`
- **Issue**: stdio.h functions are banned in safety-critical embedded code
- **Fix**: Replace with project-specific logging function or remove

### Violation 4: Unchecked Return Value (malloc)

- **Rule**: R.17.7 - The value returned by a function having non-void return type
  shall be used
- **Severity**: Required
- **Location**: Line 20 - `malloc(256);`
- **Issue**: Return value of malloc is discarded, no NULL check
- **Fix**: Capture return value and check: `void *p = malloc(256); if (p == NULL) { ... }`

### Violation 5: Use of Dynamic Memory Allocation

- **Rule**: R.21.3 - The memory allocation and deallocation functions of <stdlib.h>
  shall not be used
- **Severity**: Required
- **Location**: Line 20 - `malloc(256);`
- **Issue**: Dynamic memory allocation is prohibited in MISRA compliant code
- **Fix**: Use statically allocated buffers instead

## Summary Table

| # | Rule | Severity | Category | Description |
|---|------|----------|----------|-------------|
| 1 | R.9.1 | Required | Initialization | Uninitialized variable |
| 2 | R.13.4 | Required | Side Effects | Assignment in condition |
| 3 | R.21.6 | Required | Libraries | Banned stdio function |
| 4 | R.17.7 | Required | Functions | Unchecked return value |
| 5 | R.21.3 | Required | Libraries | Dynamic memory allocation |

## MISRA Compliance Assessment

Total violations found: 5
- Required rule violations: 5
- Advisory rule violations: 0

All violations are Required severity under MISRA C:2012 classification.
The code requires mandatory remediation before it can be considered
compliant. No deviations should be granted for these fundamental
safety violations in embedded firmware.

## Recommended Validation Tool

Run cppcheck with MISRA addon for automated verification:

```bash
cppcheck --addon=misra --enable=all --suppress=missingInclude \
    --inline-suppr sensor.c
```

Expected Result: all 5 violations detected with matching rule numbers.
