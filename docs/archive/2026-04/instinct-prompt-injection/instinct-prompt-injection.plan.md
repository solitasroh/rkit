# instinct-prompt-injection Planning Document

> **Summary**: 인스팅트 수렴 패턴을 코드 리뷰 에이전트에 직접 주입하여 실제 리뷰 동작에 영향
>
> **Project**: rkit
> **Version**: v0.9.13 (패치)
> **Author**: 노수장
> **Date**: 2026-04-10
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 인스팅트 패턴이 SessionStart additionalContext에 주입되지만 ~9KB 컨텍스트에 묻혀 코드 리뷰 시 실제 참조되지 않음 (A/B 실험 확인) |
| **Solution** | code-analyzer 에이전트 프롬프트에 인스팅트 패턴을 직접 주입하고, "Project Instinct 패턴을 우선 확인하라"는 지시를 추가 |
| **Function/UX Effect** | `/code-review` 실행 시 수렴된 인스팅트 패턴이 findings에 우선 반영됨 |
| **Core Value** | 인스팅트 학습의 실질적 가치 실현 — 학습만 되고 적용 안 되는 문제 해결 |

---

## 1. 문제 분석 (A/B 실험 결과)

### 1.1 A/B 실험 요약

동일 프롬프트로 `extractPatterns` 함수 리뷰 요청:

| 조건 | "함수 길이 → 헬퍼 분리" 언급 | "매직넘버" 언급 |
|------|:--:|:--:|
| A (인스팅트 없음) | X | X |
| B (인스팅트 있음) | X | X |

**결과**: 인스팅트 유무에 관계없이 동일한 패턴을 지적하지 않음.

### 1.2 원인

현재 주입 위치: `session-start.js` → `additionalContext` 맨 끝
- additionalContext 전체 ~9KB (PDCA status, onboarding, domain info, trigger table...)
- "Project Instinct" 섹션이 다른 정보에 묻힘
- code-analyzer 에이전트는 additionalContext를 직접 읽지 않음 — 에이전트는 자신의 프롬프트(agents/code-analyzer.md)와 imports만 참조

### 1.3 해결 방향

**인스팅트 패턴을 에이전트가 직접 읽는 곳에 주입**:

```
현재: SessionStart → additionalContext → LLM 전체 컨텍스트 (묻힘)
개선: loader.js → 파일 출력 → code-analyzer.md imports로 참조 (직접 읽음)
```

---

## 2. Scope

### 2.1 In Scope

| # | 작업 | 대상 파일 | 유형 |
|---|------|----------|------|
| 1 | 인스팅트 프로파일 파일 출력 | `lib/instinct/loader.js` | MODIFY |
| 2 | code-analyzer에 인스팅트 참조 추가 | `agents/code-analyzer.md` | MODIFY |
| 3 | L2 리뷰어 3개에도 동일 참조 추가 | `agents/{c-cpp,csharp,python}-reviewer.md` | MODIFY |
| 4 | A/B 재검증 | `tests/instinct-integration.test.js` | MODIFY |

### 2.2 핵심 설계

**loader.js에 파일 출력 함수 추가**:

```javascript
/**
 * 수렴 패턴을 .rkit/instinct/profile.md 파일로 출력.
 * 에이전트가 imports로 직접 참조할 수 있도록 마크다운 형식.
 */
function writeProfileFile() {
  const text = loadConvergedPatterns();
  const profilePath = path.join(getInstinctBase(), 'profile.md');
  if (text) {
    fs.writeFileSync(profilePath, text);
  } else {
    // 수렴 패턴 없으면 빈 안내 파일
    fs.writeFileSync(profilePath, '<!-- No converged instinct patterns yet -->');
  }
  return profilePath;
}
```

**code-analyzer.md에 imports 추가**:

```yaml
imports:
  - ${PLUGIN_ROOT}/refs/code-quality/common.md
  - ${PLUGIN_ROOT}/refs/code-quality/architecture-patterns.md
  - ${PROJECT_DIR}/.rkit/instinct/profile.md    # NEW: 인스팅트 프로파일
```

**code-analyzer.md에 지시 추가**:

```markdown
## Instinct Patterns

If `profile.md` contains "Project Instinct" patterns, check these FIRST before
other rules. These are project-specific patterns learned from previous reviews.
Report instinct-matched findings with tag `[INSTINCT]` in the Rule column.
```

### 2.3 Out of Scope

- SessionStart의 기존 additionalContext 주입은 유지 (다른 용도로 사용 가능)
- loader.js의 기존 `loadConvergedPatterns()` 인터페이스 변경 없음

---

## 3. Test Strategy

### 3.1 A/B 재검증 (핵심)

| ID | 시나리오 | 기대 결과 |
|----|---------|-----------|
| T1 | A세션 (profile.md 없음) + 코드 리뷰 | 인스팅트 패턴 미언급 |
| T2 | B세션 (profile.md 있음) + 동일 리뷰 | "함수 길이 → 헬퍼 분리" 또는 `[INSTINCT]` 태그 언급 |

```bash
# T1: profile.md 제거 후 리뷰
rm .rkit/instinct/profile.md
claude --plugin-dir . -p "collector.js의 extractPatterns 리뷰" --max-turns 3

# T2: profile.md 생성 후 동일 리뷰
node -e "require('./lib/instinct/loader').writeProfileFile()"
claude --plugin-dir . -p "collector.js의 extractPatterns 리뷰" --max-turns 3
```

### 3.2 Regression

| ID | 검증 |
|----|------|
| T3 | profile.md 없을 때 code-analyzer 정상 동작 (imports 실패 무시) |
| T4 | SessionStart의 기존 additionalContext 주입 유지 |

---

## 4. Risks

| 리스크 | 대응 |
|--------|------|
| profile.md 없을 때 imports 에러 | CC 에이전트는 imports 파일 없으면 무시 (Graceful) |
| profile.md 스테일 데이터 | SessionStart에서 매번 갱신 (writeProfileFile 호출) |
| `${PROJECT_DIR}` 미지원 가능성 | `${PLUGIN_ROOT}` 대신 상대 경로 사용 검토 |

---

## 5. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-10 | A/B 실험 기반 초안. 에이전트 직접 주입 전략 | 노수장 |
