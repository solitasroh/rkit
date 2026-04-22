"""structural-brief.md 렌더러 — AI가 설계 전반을 1페이지로 읽는 요약.

입력: ProjectGraph + (옵션) arch_check findings.
출력: Markdown 문자열. 결정론적, side effect 없음.

섹션 구성:
1. Header — 총계 (classes/edges/cycles/zone 분포)
2. Clusters — 디렉토리 2-level 기반, 내부/외부 엣지 밀도
3. Hubs — Ca+Ce 상위 10
4. Inheritance trees — 루트 기반 형태 분류 (chain/fan/forest)
5. Cycles — 엣지 타입 포함 경로
6. Anomalies — anon POD 잡음, dead 후보, arch violation

원리적 한계: 디렉토리·네임스페이스 분리가 일치하는 프로젝트에 유리. 클러스터링은
휴리스틱이며 판정 아닌 관찰. rule finding과 역할이 다름 (adversarial-review 판정
대상 아님).
설계 근거: rapp-review 고도화 축 B (memory: project_rapp_review_advancement.md)
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath

from models import Finding
from project_graph import (
    ProjectGraph, iter_class_edges, EDGE_INHERIT, EDGE_COMPOSE, EDGE_CALL,
)


HUB_TOP_N = 10
# 허브 최소 결합도 — Ca+Ce=1 인 1점짜리 잡음 제외 (dogfooding 버그 수정).
# 실제 허브는 "복수 의존 관계"를 가진 노드여야 하므로 2 이상.
HUB_MIN_SCORE = 2
CLUSTER_DEPTH = 2
ANON_TOKEN = "<anon>"
# anon + methods=0 AND fields≤4 = POD/forward-decl 잡음 휴리스틱
NOISE_FIELDS_MAX = 4


def render_structural_brief_md(
    graph: ProjectGraph,
    findings: list[Finding] | None = None,
) -> str:
    """structural-brief.md 본문 생성. graph 필수, findings는 arch violation 참조용."""
    findings = findings or []
    sections = [
        _header(graph),
        _clusters(graph),
        _hubs(graph),
        _inheritance_trees(graph),
        _cycles(graph),
        _anomalies(graph, findings),
    ]
    return "# Structural Brief\n\n" + "\n\n".join(s for s in sections if s) + "\n"


# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────

def _header(graph: ProjectGraph) -> str:
    total = len(graph.classes)
    if total == 0:
        return "- classes: 0"
    edges = iter_class_edges(graph)
    by_type = defaultdict(int)
    for _, _, t in edges:
        by_type[t] += 1
    cycles = graph.class_cycles()
    zone_counts: dict[str, int] = defaultdict(int)
    noise = 0
    for qn in graph.classes:
        zone_counts[graph.zone(qn)] += 1
        if _is_noise(graph, qn):
            noise += 1
    non_trivial = total - noise
    return "\n".join([
        f"- classes: {total} (non-trivial {non_trivial}, noise {noise})",
        f"- edges: {len(edges)} "
        f"(inherit {by_type[EDGE_INHERIT]} / "
        f"compose {by_type[EDGE_COMPOSE]} / "
        f"call {by_type[EDGE_CALL]})",
        f"- cycles: {len(cycles)}",
        f"- zones: pain {zone_counts['pain']}, useless {zone_counts['useless']},"
        f" main_sequence {zone_counts['main_sequence']},"
        f" normal {zone_counts['normal']},"
        f" isolated {zone_counts['isolated']}",
    ])


# ─────────────────────────────────────────────────────────────
# Clusters
# ─────────────────────────────────────────────────────────────

def _cluster_of(file: str) -> str:
    """파일 경로 → 상위 CLUSTER_DEPTH 세그먼트. 세그먼트 부족 시 가능한 만큼."""
    parts = PurePosixPath(file).parts
    if len(parts) <= 1:
        return "(root)"
    depth = min(CLUSTER_DEPTH, len(parts) - 1)
    return "/".join(parts[:depth])


def _compute_cluster_stats(
    graph: ProjectGraph,
) -> dict[str, dict]:
    """클러스터별 통계 — _clusters/_anomalies 공유.

    반환: {cluster_name: {classes, internal, external, cohesion}}
    """
    by_cluster: dict[str, set[str]] = defaultdict(set)
    for qn, node in graph.classes.items():
        by_cluster[_cluster_of(node.file)].add(qn)
    qn_to_cluster = {qn: _cluster_of(graph.classes[qn].file) for qn in graph.classes}
    internal: dict[str, int] = defaultdict(int)
    external: dict[str, int] = defaultdict(int)
    for f, t, _ in iter_class_edges(graph):
        cf = qn_to_cluster.get(f)
        ct = qn_to_cluster.get(t)
        if cf is None or ct is None:
            continue
        if cf == ct:
            internal[cf] += 1
        else:
            external[cf] += 1
    stats: dict[str, dict] = {}
    for cluster, members in by_cluster.items():
        n = len(members)
        stats[cluster] = {
            "classes": n,
            "internal": internal[cluster],
            "external": external[cluster],
            "cohesion": _classify_cohesion(n, internal[cluster], external[cluster]),
        }
    return stats


def _isolated_clusters(stats: dict[str, dict]) -> set[str]:
    """전체가 isolated cohesion인 클러스터 이름 set."""
    return {name for name, s in stats.items() if s["cohesion"] == "isolated"}


def _clusters(graph: ProjectGraph) -> str:
    if not graph.classes:
        return ""
    stats = _compute_cluster_stats(graph)
    lines = [
        "## Clusters (directory-based, 2-level)\n",
        "| cluster | classes | internal | external | density | cohesion |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for cluster in sorted(stats):
        s = stats[cluster]
        n = s["classes"]
        max_internal = n * (n - 1) if n > 1 else 0
        density = (s["internal"] / max_internal) if max_internal else 0.0
        lines.append(
            f"| {_md_cell(cluster)} | {n} | {s['internal']} | {s['external']} "
            f"| {density:.2f} | {s['cohesion']} |"
        )
    return "\n".join(lines)


def _classify_cohesion(n: int, internal: int, external: int) -> str:
    """클러스터 응집도 분류."""
    if n <= 1:
        return "single"
    if internal == 0 and external == 0:
        return "isolated"
    if internal == 0 and external > 0:
        return "leaky"
    if internal > external:
        return "cohesive"
    if external > internal:
        return "leaky"
    return "balanced"


# ─────────────────────────────────────────────────────────────
# Hubs
# ─────────────────────────────────────────────────────────────

def _hubs(graph: ProjectGraph) -> str:
    if not graph.classes:
        return ""
    scored: list[tuple[int, str]] = []
    for qn in graph.classes:
        score = len(graph.afferent(qn)) + len(graph.efferent(qn))
        if score >= HUB_MIN_SCORE:
            scored.append((score, qn))
    if not scored:
        return ""
    # 상위 N: score desc, qn asc (tie-break)
    scored.sort(key=lambda x: (-x[0], x[1]))
    top = scored[:HUB_TOP_N]
    lines = [
        f"## Hubs (top {len(top)} by Ca+Ce)\n",
        "| class | Ca | Ce | zone | cluster |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _score, qn in top:
        ca = len(graph.afferent(qn))
        ce = len(graph.efferent(qn))
        cluster = _cluster_of(graph.classes[qn].file)
        lines.append(
            f"| `{_md_cell(qn)}` | {ca} | {ce} "
            f"| {graph.zone(qn)} | {_md_cell(cluster)} |"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Inheritance trees
# ─────────────────────────────────────────────────────────────

def _is_inheritance_root(graph: ProjectGraph, qn: str) -> bool:
    """상속 트리 루트 = parents 해소된 부모 없음 AND NOC > 0."""
    node = graph.classes[qn]
    resolved_parents = [p for p in node.parents if p in graph.classes]
    if resolved_parents:
        return False
    return graph.noc(qn) > 0


def _collect_subtree(graph: ProjectGraph, root: str) -> tuple[int, int, int]:
    """루트 기준 서브트리 메트릭: (max_depth, total_nodes, leaves)."""
    visited: set[str] = set()
    max_depth = 0
    total = 0
    leaves = 0

    def dfs(qn: str, depth: int) -> None:
        nonlocal max_depth, total, leaves
        if qn in visited:
            return
        visited.add(qn)
        total += 1
        max_depth = max(max_depth, depth)
        children = graph.children_of(qn)
        if not children:
            leaves += 1
            return
        for c in children:
            dfs(c, depth + 1)

    dfs(root, 0)
    return max_depth, total, leaves


def _classify_tree(depth: int, leaves: int) -> str:
    """트리 형태 분류."""
    if depth == 0:
        return "isolated"
    if leaves == 1 and depth >= 2:
        return "chain"
    if depth <= 1 and leaves >= 3:
        return "fan"
    if depth >= 2 and leaves >= 3:
        return "forest"
    return "small"


def _inheritance_trees(graph: ProjectGraph) -> str:
    if not graph.classes:
        return ""
    roots = sorted(qn for qn in graph.classes if _is_inheritance_root(graph, qn))
    if not roots:
        return ""
    lines = ["## Inheritance trees (root-based)\n"]
    for root in roots:
        depth, total, leaves = _collect_subtree(graph, root)
        shape = _classify_tree(depth, leaves)
        note = ""
        # Fragile base 힌트: depth≥3 AND 루트가 concrete
        if depth >= 3 and not graph.classes[root].is_abstract:
            note = " — fragile base candidate (concrete root, depth≥3)"
        lines.append(
            f"- `{_md_cell(root)}` → {shape} "
            f"(depth={depth}, nodes={total}, leaves={leaves}){note}"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Cycles
# ─────────────────────────────────────────────────────────────

def _cycles(graph: ProjectGraph) -> str:
    cycles = graph.class_cycles()
    if not cycles:
        return ""
    edges_by_from: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for f, t, typ in iter_class_edges(graph):
        edges_by_from[f].append((t, typ))
    lines = ["## Cycles (with edge types)\n"]
    for i, cyc in enumerate(cycles, 1):
        cyc_set = set(cyc)
        types_in_cycle: set[str] = set()
        for f in cyc:
            for t, typ in edges_by_from.get(f, []):
                if t in cyc_set:
                    types_in_cycle.add(typ)
        type_label = "/".join(sorted(types_in_cycle)) if types_in_cycle else "?"
        members = ", ".join(f"`{_md_cell(c)}`" for c in cyc)
        lines.append(
            f"- Cycle {i} ({len(cyc)} classes, edges: {type_label}): {members}"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Anomalies
# ─────────────────────────────────────────────────────────────

def _is_noise(graph: ProjectGraph, qn: str) -> bool:
    """anon namespace + methods=0 + fields≤NOISE_FIELDS_MAX = POD 잡음 후보."""
    if ANON_TOKEN not in qn:
        return False
    node = graph.classes[qn]
    return len(node.methods) == 0 and len(node.fields) <= NOISE_FIELDS_MAX


def _anomalies(graph: ProjectGraph, findings: list[Finding]) -> str:
    """Anomalies 섹션.

    dead_class 후보는 **노출 안 함**. 이유: metrics.RULE_DEAD_CLASS가 기본 비활성
    (open-world 오탐 우려) — 같은 로직을 관찰 섹션에서 재노출하면 판정 파이프라인과
    불일치. 실측에서도 false positive 대부분(템플릿 인스턴스화·함수 인자 미추적).
    judging 필요하면 RULE_DEAD_CLASS enabled=true로 켜고 findings.xml에서 확인.
    """
    if not graph.classes:
        return ""
    noise = sorted(qn for qn in graph.classes if _is_noise(graph, qn))
    arch_findings = [f for f in findings if f.tool == "arch_check"]
    lines = ["## Anomalies\n"]
    any_line = False
    if noise:
        any_line = True
        lines.append(
            f"- {len(noise)} classes: anon ns + methods=0 + fields≤{NOISE_FIELDS_MAX} "
            "→ POD/forward-decl 잡음 후보"
        )
    if arch_findings:
        any_line = True
        lines.append(
            f"- {len(arch_findings)} arch violations (from arch_check)"
            " — 레이어 경계 위반"
        )
    if not any_line:
        lines.append("- (none)")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 공용 유틸
# ─────────────────────────────────────────────────────────────

def _md_cell(s: str) -> str:
    """마크다운 표 셀 안전화 — '|'·백슬래시·백틱·개행 처리."""
    return (
        s.replace("\\", "\\\\").replace("|", "\\|")
         .replace("\n", " ").replace("`", "'")
    )
