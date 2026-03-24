# Architecture Lock: {{feature}}

> Locked architecture decisions — changes require explicit unlock.

**Date**: {{date}}
**Domain**: {{domain}}
**Design Doc**: {{designDoc}}

---

## Locked Decisions

| ID | Category | Title | Description |
|----|----------|-------|-------------|
{{#decisions}}
| {{id}} | {{category}} | {{title}} | {{description}} |
{{/decisions}}

## Architecture Diagram

```mermaid
{{diagram}}
```

## Affected Paths

| Decision | Affected Paths |
|----------|---------------|
{{#decisions}}
| {{id}} | {{affectedPaths}} |
{{/decisions}}

## Rules

- Modifications to affected paths require arch-lock review
- Use `/arch-lock unlock {id}` to remove specific decision
- Use `/arch-lock unlock all` to remove all locks
- Design document changes should trigger arch-lock review
