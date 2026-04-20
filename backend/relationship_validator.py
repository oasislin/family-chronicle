"""
关系一致性校验器
在关系写入前检查数据完整性，防止矛盾、自引用、冗余关系入库。

规则矩阵（同一对人之间）：
  parent_child + sibling    → 矛盾 ✗
  parent_child + spouse     → 矛盾 ✗
  parent_child + grandparent(同向) → 冗余 ✗
  grandparent + sibling     → 矛盾 ✗
  自引用 (A == B)           → 矛盾 ✗
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass


@dataclass
class Violation:
    """校验违规项"""
    rule: str           # 规则名
    severity: str       # "error" = 必须拦截, "warning" = 建议修复
    message: str        # 人类可读描述
    rel_ids: List[str]  # 涉违规的关系 ID
    suggestion: str     # 建议操作: "remove", "keep_newer", "keep_older"


# 矛盾关系对：同一对人之间不能同时存在
CONTRADICTIONS: Set[Tuple[str, str]] = {
    ("parent_child", "sibling"),
    ("parent_child", "spouse"),
    ("grandparent_grandchild", "sibling"),
    ("grandparent_grandchild", "spouse"),
}

# 冗余规则：如果短路径存在，长路径就是冗余
# (parent_child A→B) 存在时，(grandparent_grandchild A→C) 如果 C==B 就是冗余
# 但这个需要三方检查，单独处理


def _rel_key(rel: Dict[str, Any]) -> Tuple[str, str, str]:
    """生成关系的标准化 key（person1, person2, type）"""
    p1 = rel.get("person1_id", "")
    p2 = rel.get("person2_id", "")
    rtype = rel.get("type", "")
    return (p1, p2, rtype)


def _pair_key(rel: Dict[str, Any]) -> frozenset:
    """生成无序的人物对 key"""
    return frozenset([rel.get("person1_id", ""), rel.get("person2_id", "")])


def validate_relationships(
    relationships: List[Dict[str, Any]],
    new_rels: Optional[List[Dict[str, Any]]] = None,
) -> List[Violation]:
    """
    校验关系列表的一致性。

    Args:
        relationships: 现有关系列表（每项含 id, person1_id, person2_id, type）
        new_rels: 即将新增的关系列表（可选，用于写入前检查）

    Returns:
        违规列表
    """
    violations = []

    # 合并现有 + 新增做全量检查
    all_rels = list(relationships)
    if new_rels:
        all_rels = list(new_rels) + all_rels  # 新关系优先级高

    # === 规则 1: 自引用 ===
    for rel in all_rels:
        if rel.get("person1_id") and rel["person1_id"] == rel.get("person2_id"):
            violations.append(Violation(
                rule="self_reference",
                severity="error",
                message=f"自引用关系: {rel.get('person1_id')} ↔ 自己 ({rel.get('type')})",
                rel_ids=[rel.get("id", "")],
                suggestion="remove",
            ))

    # === 规则 2: 矛盾关系对 ===
    # 按人物对分组
    pairs: Dict[frozenset, List[Dict[str, Any]]] = {}
    for rel in all_rels:
        pk = _pair_key(rel)
        if rel.get("person1_id") and rel.get("person2_id") and rel["person1_id"] != rel["person2_id"]:
            pairs.setdefault(pk, []).append(rel)

    for pair, rels in pairs.items():
        types = [r.get("type", "") for r in rels]
        # 检查所有矛盾对
        for t1, t2 in CONTRADICTIONS:
            if t1 in types and t2 in types:
                ids_with_t1 = [r.get("id", "") for r in rels if r.get("type") == t1]
                ids_with_t2 = [r.get("id", "") for r in rels if r.get("type") == t2]
                names = list(pair)
                violations.append(Violation(
                    rule="contradictory_pair",
                    severity="error",
                    message=f"矛盾关系: {names[0]} ↔ {names[1]} 同时存在 {t1} 和 {t2}",
                    rel_ids=ids_with_t1 + ids_with_t2,
                    suggestion="remove_newer" if ids_with_t2 else "remove",
                ))

        # 检查同一类型重复
        type_count = {}
        for r in rels:
            rt = r.get("type", "")
            type_count.setdefault(rt, []).append(r)
        for rt, dup_rels in type_count.items():
            if len(dup_rels) > 1:
                ids = [r.get("id", "") for r in dup_rels]
                violations.append(Violation(
                    rule="duplicate_relation",
                    severity="warning",
                    message=f"重复关系: {list(pair)} 有 {len(dup_rels)} 条 {rt}",
                    rel_ids=ids,
                    suggestion="remove_newer",
                ))

    # === 规则 3: 冗余祖孙（已有亲子路径时，祖孙是冗余）===
    # 如果 A→B 是 parent_child，且 B→C 是 parent_child，则 A→C 的 grandparent 是冗余
    parent_map: Dict[str, Set[str]] = {}  # parent -> {children}
    child_map: Dict[str, Set[str]] = {}   # child -> {parents}
    for rel in all_rels:
        if rel.get("type") == "parent_child":
            p1, p2 = rel["person1_id"], rel["person2_id"]
            parent_map.setdefault(p1, set()).add(p2)
            child_map.setdefault(p2, set()).add(p1)

    for rel in all_rels:
        if rel.get("type") == "grandparent_grandchild":
            gp, gc = rel["person1_id"], rel["person2_id"]
            # 检查是否存在 gp → middle → gc 的亲子链
            for middle in parent_map.get(gp, set()):
                if gc in parent_map.get(middle, set()):
                    violations.append(Violation(
                        rule="redundant_grandparent",
                        severity="warning",
                        message=f"冗余祖孙: {gp} ↔ {gc} (已有 {gp}→{middle}→{gc} 亲子链)",
                        rel_ids=[rel.get("id", "")],
                        suggestion="remove",
                    ))
                    break

    return violations


def auto_fix_violations(
    relationships: List[Dict[str, Any]],
    violations: List[Violation],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    自动修复违规项。

    Returns:
        (修复后的关系列表, 被移除的关系 ID 列表)
    """
    rels_by_id = {r.get("id", ""): r for r in relationships}
    removed_ids = []
    actions = []

    for v in violations:
        if v.severity != "error" and v.rule != "redundant_grandparent":
            continue  # 只自动修复 error 和冗余

        if v.suggestion == "remove":
            for rid in v.rel_ids:
                if rid in rels_by_id:
                    del rels_by_id[rid]
                    removed_ids.append(rid)
                    actions.append(f"移除: {v.message}")

        elif v.suggestion == "remove_newer":
            # 保留最早创建的，删除其余
            rels_in_violation = [rels_by_id[rid] for rid in v.rel_ids if rid in rels_by_id]
            if len(rels_in_violation) > 1:
                # 按 created_at 排序，保留最早的
                rels_in_violation.sort(key=lambda r: r.get("created_at", ""))
                for r in rels_in_violation[1:]:
                    rid = r.get("id", "")
                    if rid in rels_by_id:
                        del rels_by_id[rid]
                        removed_ids.append(rid)
                        actions.append(f"去重: 保留最早，移除 {v.message}")

    remaining = [r for r in rels_by_id.values() if r.get("id", "")]
    return remaining, removed_ids, actions


def validate_and_fix(
    relationships: List[Dict[str, Any]],
    new_rels: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Violation], List[str], List[str]]:
    """
    一站式校验 + 自动修复。

    Returns:
        (所有违规项, 被移除的关系 ID, 修复操作描述)
    """
    violations = validate_relationships(relationships, new_rels)
    if not violations:
        return [], [], []

    all_rels = list(relationships)
    if new_rels:
        all_rels = list(new_rels) + all_rels

    remaining, removed, actions = auto_fix_violations(all_rels, violations)
    return violations, removed, actions
