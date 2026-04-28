"""
关系推导引擎 v2 — BFS 扩散式推导

核心原则：
- 原子关系：parent_child, spouse（触发级联推导）
- 派生关系：sibling（至少一个共同父母）, step_parent_child（不扩散）
- 推导是 BFS：新关系建立后，从涉及的两个节点出发，遍历一层原子关系，推导出新的关系
- 每个推导出的关系同样触发扩散，直到无新关系产生

规则：
1. 共同子女 → 配偶（A和B都是C的父/母 → A和B是配偶）
2. 配偶 + 一方是父/母 → 另一方也是父/母
3. 至少一个共同父母 → 兄弟姐妹
4. 干爹/干妈的配偶 → 干妈/干爹（仅此一条）
5. 父母→子女是唯一的（同一个人只能有一个父亲、一个母亲）
6. 配偶非唯一（允许再婚）
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict


def derive_relationships_v2(
    persons_or_graph: Any,
    relationships: Optional[List[dict]] = None,
    new_rel: Optional[dict] = None,
) -> List[dict]:
    """
    BFS 扩散式关系推导。支持直接传入 FamilyGraph 对象。

    Args:
        persons_or_graph: FamilyGraph 对象，或者 {id: {gender, ...}} 字典
        relationships: 如果第一个参数是字典，则此参数为已有关系列表 [{person_a, person_b, type, subtype?}, ...]
        new_rel: 即将新增的单条关系（触发推导的种子）

    Returns:
        需要新增的推导关系列表 [{person_a, person_b, type, source}]
    """
    # 如果传入的是 FamilyGraph
    is_graph = hasattr(persons_or_graph, 'people') and hasattr(persons_or_graph, 'relationships')
    
    if is_graph:
        graph = persons_or_graph
        # 转换为内部使用的格式
        internal_persons = {
            pid: {"gender": p.gender.value if hasattr(p.gender, 'value') else str(p.gender)}
            for pid, p in graph.people.items()
        }
        internal_rels = []
        for r in graph.relationships.values():
            internal_rels.append({
                "person_a": r.person1_id,
                "person_b": r.person2_id,
                "type": r.type.value if hasattr(r.type, 'value') else str(r.type),
                "subtype": r.subtype
            })
        
        # 调用核心推导逻辑
        derived_rels = _derive_logic(internal_persons, internal_rels, new_rel)
        
        # 将推导出的关系添加回 graph
        from models import Relationship, RelationshipType
        results = []
        for r in derived_rels:
            try:
                rtype = RelationshipType(r['type'])
            except ValueError:
                rtype = RelationshipType.OTHER
                
            new_r = Relationship(
                person1_id=r['person_a'],
                person2_id=r['person_b'],
                rel_type=rtype,
                is_inferred=True
            )
            graph.add_relationship(new_r)
            
            p1 = graph.get_person(r['person_a'])
            p2 = graph.get_person(r['person_b'])
            results.append({
                'person_a': p1.name if p1 else r['person_a'],
                'person_b': p2.name if p2 else r['person_b'],
                'type': r['type'],
                'source': r['source']
            })
        return results
    else:
        # 原有的字典格式处理
        return _derive_logic(persons_or_graph, relationships or [], new_rel)


def _derive_logic(
    persons: Dict[str, dict],
    relationships: List[dict],
    new_rel: Optional[dict] = None,
) -> List[dict]:
    """核心推导逻辑（原 derive_relationships_v2 的实现）"""
    # 构建关系索引
    # parents[child] = {parent_name, ...}
    # children[parent] = {child_name, ...}
    # spouses[person] = {spouse_name, ...}
    # godparents[child] = {godparent_name, ...}
    # godchildren[godparent] = {godchild_name, ...}
    # siblings[person] = {sibling_name, ...} (已存在的)

    parents = defaultdict(set)       # child -> set of parent names
    children = defaultdict(set)      # parent -> set of child names
    spouses = defaultdict(set)       # person -> set of spouse names
    godparents = defaultdict(set)    # godchild -> set of godparent names
    godchildren = defaultdict(set)   # godparent -> set of godchild names
    existing_siblings = defaultdict(set)  # person -> set of sibling names

    # 用于去重的关系集合
    existing = set()

    def _norm_key(a: str, b: str, t: str) -> Tuple:
        """标准化关系key（无序对+类型）"""
        return (min(a, b), max(a, b), t)

    def _add_existing(a: str, b: str, t: str):
        existing.add(_norm_key(a, b, t))

    def _exists(a: str, b: str, t: str) -> bool:
        return _norm_key(a, b, t) in existing

    # 加载已有关系到索引
    for r in relationships:
        a, b, t = r['person_a'], r['person_b'], r['type']
        _add_existing(a, b, t)

        if t == 'parent_child':
            # 约定：person_a 是父母，person_b 是子女（长辈→晚辈）
            parents[b].add(a)
            children[a].add(b)
        elif t == 'spouse':
            spouses[a].add(b)
            spouses[b].add(a)
        elif t == 'sibling':
            existing_siblings[a].add(b)
            existing_siblings[b].add(a)
        elif t == 'godparent_godchild':
            # person_a = 干爹/干妈, person_b = 干儿子/干女儿
            godchildren[a].add(b)
            godparents[b].add(a)

    # 如果有新关系种子，先加入索引
    if new_rel:
        a, b, t = new_rel['person_a'], new_rel['person_b'], new_rel['type']
        _add_existing(a, b, t)
        if t == 'parent_child':
            parents[b].add(a)
            children[a].add(b)
        elif t == 'spouse':
            spouses[a].add(b)
            spouses[b].add(a)
        elif t == 'godparent_godchild':
            godchildren[a].add(b)
            godparents[b].add(a)

    new_rels = []
    # BFS 队列：待处理的人物
    queue = []
    processed_edges = set()  # 避免重复处理同一条推导

    def enqueue(person: str):
        if person not in queue:
            queue.append(person)

    def add_derived(a: str, b: str, rtype: str, source: str):
        """添加推导关系（带去重）"""
        if a == b:
            return
        edge_key = (a, b, rtype, source)
        if edge_key in processed_edges:
            return
        processed_edges.add(edge_key)

        if not _exists(a, b, rtype):
            _add_existing(a, b, rtype)
            new_rels.append({
                "person_a": a,
                "person_b": b,
                "type": rtype,
                "source": source,
            })
            # 推导出新关系后，将涉及的人物加入队列继续扩散
            enqueue(a)
            enqueue(b)

    # 初始化队列
    if new_rel:
        enqueue(new_rel['person_a'])
        enqueue(new_rel['person_b'])
    else:
        # 全量推导：将所有人物加入队列
        for pid in persons.keys():
            enqueue(pid)

    # ========== BFS 扩散 ==========
    while queue:
        person = queue.pop(0)
        person_gender = persons.get(person, {}).get('gender', 'unknown')

        # ── 遍历此人的所有子女 ──
        for child in children.get(person, set()):
            child_gender = persons.get(child, {}).get('gender', 'unknown')

            # 规则2: 配偶 + 一方是父/母 → 另一方也是父/母
            for spouse in spouses.get(person, set()):
                spouse_gender = persons.get(spouse, {}).get('gender', 'unknown')
                # spouse 也应该是 child 的父/母
                add_derived(spouse, child, 'parent_child',
                           f'夫妻推导:{person}是{child}的父/母,{spouse}是配偶→也是父/母')

            # 规则3: 同一父母的其他子女 → 兄弟姐妹
            for sibling in children.get(person, set()):
                if sibling != child:
                    sib_gender = persons.get(sibling, {}).get('gender', 'unknown')
                    # 区分兄弟/姐妹/兄妹/姐弟
                    add_derived(child, sibling, 'sibling',
                               f'同父母推导:{person}是共同父/母')

        # ── 遍历此人的所有父母 ──
        for parent in parents.get(person, set()):
            # 规则3: 同一父母的其他子女 → 兄弟姐妹
            for sibling in children.get(parent, set()):
                if sibling != person:
                    add_derived(person, sibling, 'sibling',
                               f'同父母推导:{parent}是共同父/母')

            # 规则5: 父母→子女唯一性检查
            # 如果 person 已经有一个同性别的父/母，新添加的同性别父/母会替换
            # 这个在写入前检查，不在推导阶段处理

        # ── 遍历此人的所有配偶 ──
        for spouse in spouses.get(person, set()):
            # 规则2: 配偶的子女 → 也是此人的子女
            for child in children.get(spouse, set()):
                add_derived(person, child, 'parent_child',
                           f'夫妻推导:{spouse}是{child}的父/母,{person}是配偶→也是父/母')

            # 规则1: 如果此人的子女也是spouse的子女 → 已由规则2覆盖
            # 共同子女 → 配偶（反向验证）
            for child in children.get(person, set()):
                if child in children.get(spouse, set()):
                    # 已经是配偶了，跳过
                    pass

        # ── 规则1: 共同子女 → 配偶 ──
        # 遍历此人的所有子女，检查是否有其他人也是同一子女的父/母
        for child in children.get(person, set()):
            for other_parent in parents.get(child, set()):
                if other_parent != person:
                    # 检查是否一方是另一方的子女（避免父女配对推导为配偶）
                    if person in children.get(other_parent, set()):
                        continue
                    if other_parent in children.get(person, set()):
                        continue
                    add_derived(person, other_parent, 'spouse',
                               f'共同子女推导:{child}是共同子女')

        # ── 规则4: 干爹/干妈的配偶 → 干妈/干爹（仅此一条）──
        for godchild in godchildren.get(person, set()):
            for spouse in spouses.get(person, set()):
                add_derived(spouse, godchild, 'godparent_godchild',
                           f'干亲配偶推导:{person}是{godchild}的干爹/妈,{spouse}是配偶')

        for godparent in godparents.get(person, set()):
            for spouse in spouses.get(person, set()):
                add_derived(spouse, godparent, 'godparent_godchild',
                           f'干亲配偶推导:{godparent}是{person}的干爹/妈,{spouse}是配偶')

    return new_rels


def get_sibling_type(gender_a: str, gender_b: str) -> str:
    """
    根据两个人的性别返回兄弟姐妹的具体称谓。

    Returns: "兄弟", "姐妹", "兄妹", "姐弟"
    """
    if gender_a == 'male' and gender_b == 'male':
        return '兄弟'
    elif gender_a == 'female' and gender_b == 'female':
        return '姐妹'
    elif gender_a == 'male' and gender_b == 'female':
        return '兄妹'
    elif gender_a == 'female' and gender_b == 'male':
        return '姐弟'
    return '兄弟姐妹'


def check_parent_uniqueness(
    new_parent: str,
    child: str,
    parent_gender: str,
    parents: Dict[str, Set[str]],
    persons: Dict[str, dict],
) -> Optional[str]:
    """
    检查父母唯一性约束。
    一个人只能有一个父亲（male）和一个母亲（female）。

    Returns:
        如果需要替换，返回被替换的旧父母名称；否则返回 None
    """
    for existing_parent in parents.get(child, set()):
        if existing_parent == new_parent:
            continue
        existing_gender = persons.get(existing_parent, {}).get('gender', 'unknown')
        if existing_gender == parent_gender:
            return existing_parent
    return None


if __name__ == '__main__':
    # 测试：母亲已有2个儿子，新增第3个儿子
    persons = {
        "朱雪兰": {"gender": "female"},
        "林绿洲的爸爸": {"gender": "male"},
        "林绿洲": {"gender": "male"},
        "林小明": {"gender": "male"},
        "林小红": {"gender": "female"},
    }
    existing_rels = [
        {"person_a": "朱雪兰", "person_b": "林绿洲", "type": "parent_child"},
        {"person_a": "林绿洲的爸爸", "person_b": "林绿洲", "type": "parent_child"},
        {"person_a": "朱雪兰", "person_b": "林绿洲的爸爸", "type": "spouse"},
        {"person_a": "朱雪兰", "person_b": "林小明", "type": "parent_child"},
        {"person_a": "林绿洲的爸爸", "person_b": "林小明", "type": "parent_child"},
        {"person_a": "林绿洲", "person_b": "林小明", "type": "sibling"},
    ]

    # 新增：朱雪兰 → 林小红（母亲生了女儿）
    new_rel = {"person_a": "朱雪兰", "person_b": "林小红", "type": "parent_child"}

    derived = _derive_logic(persons, existing_rels, new_rel)
    print("推导出的新关系:")
    for r in derived:
        print(f"  {r['person_a']} --[{r['type']}]--> {r['person_b']} ({r['source']})")

    print("\n--- 预期 ---")
    print("  林绿洲的爸爸 → 林小红 (parent_child: 夫妻推导)")
    print("  林小红 ↔ 林绿洲 (sibling: 同父母推导)")
    print("  林小红 ↔ 林小明 (sibling: 同父母推导)")
