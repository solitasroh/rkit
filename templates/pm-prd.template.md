---
template: pm-prd
version: 1.0
description: PM Agent Team PRD output template. Combines Discovery, Strategy, Research analysis with Beachhead + GTM + PRD 8-section.
variables:
  - feature: Feature name
  - date: Creation date (YYYY-MM-DD)
  - author: Author
---

# {feature} - Product Requirements Document

> **Date**: {date}
> **Author**: {author}
> **Method**: bkit PM Agent Team (based on pm-skills by Pawel Huryn, MIT)
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | {Core problem in 1-2 sentences} |
| **Solution** | {Proposed solution in 1-2 sentences} |
| **Target User** | {Primary user segment} |
| **Core Value** | {Why this matters} |

---

## 1. Opportunity Discovery

### 1.1 Desired Outcome

{Measurable business/product outcome}

### 1.2 Opportunity Solution Tree

```
Outcome: {desired outcome}
├── Opportunity 1: {customer need/pain}
│   ├── Solution A: {approach}
│   └── Solution B: {approach}
├── Opportunity 2: {customer need/pain}
│   ├── Solution C: {approach}
│   └── Solution D: {approach}
└── Opportunity 3: {customer need/pain}
    └── Solution E: {approach}
```

### 1.3 Prioritized Opportunities

| # | Opportunity | Importance | Satisfaction | Score |
|---|------------|------------|--------------|-------|
| 1 | {opportunity} | {0-1} | {0-1} | {score} |
| 2 | {opportunity} | {0-1} | {0-1} | {score} |
| 3 | {opportunity} | {0-1} | {0-1} | {score} |

### 1.4 Recommended Experiments

| # | Tests Assumption | Method | Success Criteria |
|---|-----------------|--------|-----------------|
| 1 | {assumption} | {method} | {criteria} |

---

## 2. Value Proposition & Strategy

### 2.1 JTBD Value Proposition (6-Part)

| Part | Content |
|------|---------|
| **Who** | {target customer segment} |
| **Why** | {core problem, JTBD} |
| **What Before** | {current situation, existing solutions} |
| **How** | {how product solves the problem} |
| **What After** | {improved outcome} |
| **Alternatives** | {competitive alternatives, why choose us} |

**Value Proposition Statement**: {1-2 sentence summary}

### 2.2 Lean Canvas

| Section | Content |
|---------|---------|
| **Problem** | {top 3 problems} |
| **Solution** | {top 3 features} |
| **UVP** | {unique value proposition} |
| **Unfair Advantage** | {defensibility} |
| **Customer Segments** | {target segments} |
| **Channels** | {acquisition channels} |
| **Revenue Streams** | {revenue model} |
| **Cost Structure** | {key costs} |
| **Key Metrics** | {north star + supporting metrics} |

---

## 3. Market Research

### 3.1 User Personas

#### Persona 1: {name}

| Attribute | Details |
|-----------|---------|
| **Demographics** | {age, role, context} |
| **Primary JTBD** | {core job to be done} |
| **Pain Points** | 1. {pain} 2. {pain} 3. {pain} |
| **Desired Gains** | 1. {gain} 2. {gain} 3. {gain} |
| **Unexpected Insight** | {counterintuitive finding} |
| **Product Fit** | {how product addresses needs} |

#### Persona 2: {name}

{same structure}

#### Persona 3: {name}

{same structure}

### 3.2 Competitive Landscape

| Competitor | Strengths | Weaknesses | Our Opportunity |
|-----------|-----------|------------|-----------------|
| {comp 1} | {strengths} | {weaknesses} | {opportunity} |
| {comp 2} | {strengths} | {weaknesses} | {opportunity} |
| {comp 3} | {strengths} | {weaknesses} | {opportunity} |
| {comp 4} | {strengths} | {weaknesses} | {opportunity} |
| {comp 5} | {strengths} | {weaknesses} | {opportunity} |

**Differentiation Strategy**: {key differentiators to emphasize}

### 3.3 Market Sizing

| Metric | Current Estimate | 3-Year Projection |
|--------|-----------------|-------------------|
| **TAM** | {total addressable market} | {projection} |
| **SAM** | {serviceable addressable} | {projection} |
| **SOM** | {serviceable obtainable} | {projection} |

**Key Assumptions**: {numbered list of critical assumptions}

---

## 4. Go-To-Market

### 4.1 Beachhead Segment

| Criteria | Score (1-5) | Evidence |
|----------|:-----------:|---------|
| Burning Pain | {score} | {evidence} |
| Willingness to Pay | {score} | {evidence} |
| Winnable Share | {score} | {evidence} |
| Referral Potential | {score} | {evidence} |

**Primary Beachhead**: {selected segment}
**90-Day Acquisition Plan**: {key actions}

### 4.2 GTM Strategy

| Element | Details |
|---------|---------|
| **Channels** | {primary acquisition channels} |
| **Messaging** | {core message for beachhead segment} |
| **Success Metrics** | {KPIs and targets} |
| **Launch Timeline** | Pre-launch / Launch / Post-launch phases |

---

## 5. Product Requirements (PRD)

### 5.1 Summary

{2-3 sentence product summary}

### 5.2 Background & Context

{Why now? What changed? What became possible?}

### 5.3 Objectives & Key Results

| Objective | Key Result | Target |
|-----------|-----------|--------|
| {objective} | {measurable KR} | {target value} |

### 5.4 Market Segments

{Target segments with constraints - markets defined by problems/JTBD, not demographics}

### 5.5 Value Propositions

{Customer jobs, gains, pains solved - reference Section 2.1}

### 5.6 Solution (Key Features)

| Feature | Description | Priority | Addresses |
|---------|-------------|----------|-----------|
| {feature} | {description} | Must/Should/Could | {which opportunity/pain} |

### 5.7 Assumptions & Risks

| # | Assumption | Category | Confidence | Validation Method |
|---|-----------|----------|------------|-------------------|
| 1 | {assumption} | Value/Usability/Feasibility/Viability | High/Med/Low | {method} |

### 5.8 Release Plan

| Phase | Scope | Timeframe |
|-------|-------|-----------|
| v1 (MVP) | {core features} | {relative timeframe} |
| v2 | {enhancements} | {relative timeframe} |

---

## Attribution

This PRD was generated by bkit PM Agent Team.
Frameworks based on [pm-skills](https://github.com/phuryn/pm-skills) by Pawel Huryn (MIT License).

- Opportunity Solution Tree: Teresa Torres, *Continuous Discovery Habits*
- Value Proposition: JTBD 6-Part (Pawel Huryn & Aatir Abdul Rauf)
- Lean Canvas: Ash Maurya
- Beachhead Segment: Geoffrey Moore, *Crossing the Chasm*
