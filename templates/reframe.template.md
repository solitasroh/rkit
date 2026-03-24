# Reframe: {{feature}}

> Embedded Challenge Protocol — Systematic problem validation before PDCA

**Date**: {{date}}
**Domain**: {{domain}}
**Mode**: {{mode}} (Full: Q1-Q21 / Standard: Q1-Q15 / Quick: Q1,Q3,Q5,Q7,Q11,Q13,Q18)

---

## Phase 1: Problem Validation

### Q1. Problem Statement (Wedell-Wedellsborg)
> "What problem are you trying to solve?" — One sentence.

**Answer**:

### Q2. Demand Reality (Garry Tan)
> "Who is experiencing this problem, and what is the evidence?" — Field data, issue numbers, measurements required.

**Answer**:

### Q3. Status Quo Cost (Garry Tan)
> "What happens if we do nothing?" — Quantify the cost.

**Answer**:

### Q4. Reframing (Wedell-Wedellsborg)
> "Can you frame this problem completely differently?"

**Original framing**:
**Reframed**:

---

## Phase 2: Assumption Surfacing

### Q5. Assumption List (David Bland)
> "What must be true for this solution to work?" — List all assumptions.

| # | Assumption | Evidence Level | Risk |
|---|-----------|---------------|------|
| 1 | | none / weak / strong | high / medium / low |

### Q6. Leap of Faith (David Bland)
> "Which assumptions have zero evidence?" — These must be tested first.

**Leap of Faith assumptions**:

### Q7. Pre-Mortem (Gary Klein)
> "3 months from now this failed. What went wrong?" — 5 failure scenarios.

| # | Failure Scenario | Likelihood | Impact | Mitigation |
|---|-----------------|-----------|--------|------------|
| 1 | | | | |

### Q8. Critical Risk (Gary Klein)
> "What is the most costly/dangerous failure mode? How do we prevent it?"

**Critical failure**:
**Prevention**:

---

## Phase 3: Solution Challenge

### Q9. Five Whys (Toyota)
> "Why this solution?" — Trace 5 levels deep to root cause.

1. Why?
2. Why?
3. Why?
4. Why?
5. Why? → **Root cause**:

### Q10. MECE Alternatives (McKinsey)
> "Have you considered all categories of solutions?"

| Category | Considered? | Reason to include/exclude |
|----------|:-----------:|--------------------------|
| | | |

### Q11. Narrowest Wedge (Garry Tan)
> "What is the smallest version that proves the concept?"

**MVP scope**:

### Q12. Second-Order Effects (Garry Tan)
> "What are the secondary impacts?" — Flash/RAM, CPU load, power, build time, maintenance complexity.

| Impact Area | Effect | Acceptable? |
|-------------|--------|:-----------:|
| | | |

---

## Phase 4: Measurement Contract

### Q13. Done Criteria
> "How do you know this is 'done'?" — Numeric pass/fail criteria.

| Criterion | Target | Measurement Method |
|-----------|--------|-------------------|
| | | |

### Q14. Measurement Tools
> "How do you measure it?" — Specify tools (logic analyzer, profiler, unit test, oscilloscope).

**Tools**:

### Q15. Worst Case
> "What happens in the worst case? (not the typical case)" — Embedded systems fail at the margins.

**Worst case scenario**:
**Margin analysis**:

---

## Phase 5: Code Quality Challenge

### Q16. Codebase Consistency
> "Is it consistent with existing codebase patterns?" — Naming, error handling, module structure, directory layout.

**Assessment**:

### Q17. Dependency Direction
> "Is the dependency direction correct?" — No circular references? Upper layers only reference lower layers?

**Assessment**:

### Q18. Error Handling Strategy
> "What is the error handling strategy?" — fail-fast vs retry vs graceful degradation.

**Strategy**:
**Error propagation path**:

### Q19. Concurrency / Shared Resources
> "Are there concurrency/shared resource issues?" — Multi-task/multi-thread shared resource protection, deadlock/race potential.

**Assessment**:

### Q20. Testability
> "Is the structure testable?" — Can external dependencies (hardware, filesystem, network) be mocked/stubbed? Is pure logic separated from I/O?

**Assessment**:

### Q21. API/Interface Contract
> "Is the API/interface contract clear?" — Input range, return value meaning, failure conditions specified? Hard to misuse?

**Assessment**:

---

## Summary

### Problem Definition Comparison

| | Before Reframe | After Reframe |
|--|---------------|--------------|
| **Problem** | | |
| **Root Cause** | | |
| **Solution** | | |
| **MVP** | | |

### Key Risks

| Risk | Mitigation | Owner |
|------|-----------|-------|
| | | |

### Next Step
→ `/pdca plan {{feature}}` with this reframe as context
