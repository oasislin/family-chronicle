"""
关系推导补全引擎
从已知关系推导缺失的关系

推导规则：
1. 夫妻 + 一方是孩子的父/母 → 另一方是孩子的母/父
2. 同父或同母 → 兄弟姐妹
3. A是B的父亲 + B是C的父亲 → A是C的祖父
4. A是B的父亲 + C是B的配偶 → A是C的公公/岳父
"""


def derive_relationships(persons: dict, relationships: list) -> list:
    """
    从现有关系推导缺失关系，返回新增关系列表

    persons: {name: {gender, ...}}
    relationships: [{person_a, person_b, type}, ...]
    """
    existing = set()
    for r in relationships:
        key = (r['person_a'], r['person_b'], r['type'])
        existing.add(key)
        # 反向也加入
        existing.add((r['person_b'], r['person_a'], r['type']))

    new_rels = []

    def add_rel(a, b, rtype, source="derived"):
        """添加关系（如果不存在）"""
        if a == b:
            return
        key = (a, b, rtype)
        if key not in existing:
            existing.add(key)
            existing.add((b, a, rtype))
            new_rels.append({"person_a": a, "person_b": b, "type": rtype, "source": source})

    # 建立索引
    # parent[child] = {parent_name, ...}
    # children[parent] = {child_name, ...}
    # spouses[person] = {spouse_name, ...}
    # siblings[person] = {sibling_name, ...}

    parents = {}   # child -> set of parents
    children = {}  # parent -> set of children
    spouses = {}   # person -> set of spouses

    for r in relationships:
        a, b, t = r['person_a'], r['person_b'], r['type']
        if t == 'parent_child':
            # A is B's parent (A→B means A is parent of B, or B is parent of A)
            # 需要判断方向：通常 辈分高的 是 父母
            # 简单处理：如果 A 的性别是 male 且 B 是 A 的 "儿子"/"女儿" → A 是 B 的父亲
            parents.setdefault(b, set()).add(a)
            children.setdefault(a, set()).add(b)
        elif t in ('spouse', '夫妻'):
            spouses.setdefault(a, set()).add(b)
            spouses.setdefault(b, set()).add(a)

    # ============ 规则1: 夫妻 + 父子 → 母子（或反向）============
    # 如果 A 和 B 是夫妻，A 是 C 的父亲 → B 是 C 的母亲
    # 如果 A 和 B 是夫妻，A 是 C 的母亲 → B 是 C 的父亲
    for person, spouse_set in spouses.items():
        for spouse in spouse_set:
            for child in children.get(person, set()):
                # person 是 child 的父/母
                person_gender = persons.get(person, {}).get('gender', 'unknown')
                spouse_gender = persons.get(spouse, {}).get('gender', 'unknown')

                if person_gender == 'male' and spouse_gender == 'female':
                    add_rel(spouse, child, 'parent_child', '夫妻推导:夫→父,妻→母')
                elif person_gender == 'female' and spouse_gender == 'male':
                    add_rel(spouse, child, 'parent_child', '夫妻推导:妻→母,夫→父')

    # ============ 规则2: 同父母 → 兄弟姐妹 ============
    for child, parent_set in parents.items():
        for parent in parent_set:
            for sibling in children.get(parent, set()):
                if sibling != child:
                    add_rel(child, sibling, 'sibling', '同父母推导')

    # ============ 规则3: A是B的父亲 + B是C的父亲 → A是C的祖父 ============
    for child, parent_set in list(parents.items()):
        for parent in parent_set:
            for grandchild in children.get(child, set()):
                parent_gender = persons.get(parent, {}).get('gender', 'unknown')
                if parent_gender == 'male':
                    add_rel(parent, grandchild, 'grandparent', '祖父推导')
                elif parent_gender == 'female':
                    add_rel(parent, grandchild, 'grandparent', '祖母推导')

    # ============ 规则4: 兄弟的传递性 ============
    # 如果 A和B是兄弟, B和C是兄弟 → A和C是兄弟
    # (由规则2已经覆盖了大部分情况)

    # ============ 规则5: 共同子女 → 配偶 ============
    # 如果 A 是 C 的父/母，B 也是 C 的父/母 → A 和 B 是配偶
    # 这是规则1的反向：规则1是「夫妻+父子→另一方也是父子」
    # 规则5是「两个都是某孩子的父/母→他们是夫妻」
    for child, parent_set in parents.items():
        parent_list = list(parent_set)
        for i in range(len(parent_list)):
            for j in range(i + 1, len(parent_list)):
                a, b = parent_list[i], parent_list[j]
                # 两人都不是对方的孩子（避免辈分混乱）
                if a not in children.get(b, set()) and b not in children.get(a, set()):
                    add_rel(a, b, 'spouse', '共同子女推导')

    return new_rels


def apply_derivation(case_id: str, actions: list, all_persons: dict, all_rels: list) -> list:
    """
    在单条用例处理后，检查是否需要推导补全

    返回: 需要补充的 actions
    """
    extra_actions = []

    # 检查是否有新建的夫妻关系
    new_spouse_rels = [a for a in actions
                       if a.get('type') == 'ADD_RELATIONSHIP'
                       and a.get('relation', a.get('rel', '')) in ('spouse', '夫妻')]

    # 检查是否有新建的父子关系
    new_parent_rels = [a for a in actions
                       if a.get('type') == 'ADD_RELATIONSHIP'
                       and a.get('relation', a.get('rel', '')) == 'parent_child']

    for spouse_rel in new_spouse_rels:
        a = spouse_rel.get('a', spouse_rel.get('person_a', ''))
        b = spouse_rel.get('b', spouse_rel.get('person_b', ''))

        # 查找 a 或 b 的所有子女
        for rel in all_rels:
            if rel['type'] == 'parent_child':
                if rel['person_a'] == a:
                    # a 是某人的父/母，b(配偶)也应该是
                    extra_actions.append({
                        'type': 'DERIVE_RELATIONSHIP',
                        'person_a': b,
                        'person_b': rel['person_b'],
                        'relation': 'parent_child',
                        'reason': f'{a}和{b}是夫妻，{a}是{rel["person_b"]}的父/母→{b}也是父/母'
                    })
                elif rel['person_a'] == b:
                    extra_actions.append({
                        'type': 'DERIVE_RELATIONSHIP',
                        'person_a': a,
                        'person_b': rel['person_b'],
                        'relation': 'parent_child',
                        'reason': f'{a}和{b}是夫妻，{b}是{rel["person_b"]}的父/母→{a}也是父/母'
                    })

    return extra_actions


if __name__ == '__main__':
    # 测试
    persons = {
        "爷爷": {"gender": "male"},
        "奶奶": {"gender": "female"},
        "爸爸": {"gender": "male"},
        "大伯": {"gender": "male"},
        "姑姑": {"gender": "female"},
        "妈妈": {"gender": "female"},
        "我": {"gender": "male"},
    }
    rels = [
        {"person_a": "爷爷", "person_b": "爸爸", "type": "parent_child"},
        {"person_a": "爷爷", "person_b": "大伯", "type": "parent_child"},
        {"person_a": "爷爷", "person_b": "姑姑", "type": "parent_child"},
        {"person_a": "爷爷", "person_b": "奶奶", "type": "spouse"},
        {"person_a": "爸爸", "person_b": "妈妈", "type": "spouse"},
        {"person_a": "爸爸", "person_b": "我", "type": "parent_child"},
    ]

    new = derive_relationships(persons, rels)
    print("推导出的新关系:")
    for r in new:
        print(f"  {r['person_a']} --[{r['type']}]--> {r['person_b']} ({r['source']})")
