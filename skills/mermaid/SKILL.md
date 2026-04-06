---
name: mermaid
classification: capability
deprecation-risk: low
domain: all
description: |
  Mermaid v8.8.0 다이어그램 작성 규칙. subgraph ID 필수, flowchart/direction/& 금지.
  Triggers: mermaid, diagram, 다이어그램, ダイアグラム
user-invocable: false
allowed-tools: [Read, Write, Edit]
pdca-phase: design
---

# Mermaid Rules (v8.8.0)

## Absolute Rules (violation = 100% render error)

1. **`flowchart` forbidden** → use `graph` only
2. **`direction` forbidden** → no `direction TB/LR` inside subgraph (requires 9.3+)
3. **All subgraphs need ID** → `subgraph ID["label"]` format only
4. **`&` operator forbidden** → `A --> B & C` is invalid, use separate lines
5. **Node IDs: alphanumeric only** → no Korean, special chars, spaces
6. **Labels with special chars/Korean/HTML must use `[""]`**

## Node Labels

```mermaid
%% Good
A["ApplicationContext"]
B["Observable<br/>Filter"]

%% Bad — syntax error
A[ApplicationContext<br/>Composition Root]    %% no quotes + <br/> → error
```

`[""]` required when label contains: `<br/>`, HTML tags, `·`, `↔`, `()`, `<>`, `/`, `+`, `-`, Korean, multi-word with spaces.

## Subgraph — Most Common Error Source

Format: `subgraph AlphanumericID["Display Label"]`

```mermaid
%% Good
graph TD
    subgraph APP["apps/ui (namespace ui)"]
        subgraph MVVM["MVVM"]
            A["main.qml"]
        end
    end

%% Bad
flowchart TD                        %% flowchart → error
    subgraph APP["apps/ui"]
        direction TB                %% direction → error
    end
subgraph "apps/ui"                  %% no ID → error
```

## Connections — No `&` Operator

```mermaid
%% Good — separate lines
CTX --> LOC
CTX --> SVC
CTX --> DSP

%% Bad — & operator error
CTX --> LOC & SVC & DSP
```

## Style

- Place `style` declarations at the bottom of the diagram
- Use `classDef` + `class` for reusable styles
- Always specify `color` when using `fill` (readability)

## Readability

- **Max 15 nodes** per diagram — split if more
- Large systems: split by layer/role into multiple smaller diagrams
- Labels: class/file name only (no paths), connection labels: 1 verb

## Diagram Type Selection

| Purpose | Type |
|---------|------|
| Module/layer structure | `graph TD` |
| Call relationships (L→R) | `graph LR` |
| Sequence/scenario | `sequenceDiagram` |
| Class relationships | `classDiagram` |
| State transitions | `stateDiagram-v2` |

## Post-Generation Checklist

1. No `flowchart` keyword?
2. No `direction` keyword?
3. All `subgraph` have alphanumeric ID?
4. No `&` operator?
5. No Korean/special chars in node IDs?
6. All special char/Korean labels wrapped in `[""]`?
7. No duplicate node IDs across entire diagram?
8. No empty subgraphs? (min 1 node required)
9. Node count ≤ 15?
10. Subgraph nesting ≤ 3 levels?
