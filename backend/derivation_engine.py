"""
关系推导传播引擎 v2
BFS from affected nodes, traversing all first-level atomic relationships.

Rules:
  1. 共同父母 → 兄弟姐妹
  2. 配偶 + 一方是父/母 → 另一方也是父/母 (co-parent)
  3a. 父母视角: 子女有另一父母 → 配偶推导
  3b. 子女视角: 共同父母 → 配偶推导
  4. 配偶传递性（需实际共同子女验证）

Constraints:
  - parent_child/sibling 不能同时存在于同对人之间
  - parent_child 有向 (parent→child)
  - spouse/sibling 对称
"""

from collections import deque
from typing import Set, Tuple


def propagate_from_nodes(graph, seed_ids: set) -> list:
    """从种子节点出发 BFS 推导新关系"""
    existing: Set[Tuple[str, str, str]] = set()
    derived: Set[Tuple[str, str, str]] = set()

    def _rt(r):
        return r.type.value if hasattr(r.type, 'value') else str(r.type)

    for r in graph.relationships.values():
        t = _rt(r)
        if t in ('spouse', 'sibling'):
            existing.add((r.person1_id, r.person2_id, t))
            existing.add((r.person2_id, r.person1_id, t))
        elif t == 'parent_child':
            existing.add((r.person1_id, r.person2_id, t))
        else:
            existing.add((r.person1_id, r.person2_id, t))
            existing.add((r.person2_id, r.person1_id, t))

    def _add(a, b, rtype):
        if a == b: return False
        key = (a, b, rtype)
        if key in existing or key in derived: return False
        all_r = existing | derived
        if rtype == 'spouse' and ((a,b,'parent_child') in all_r or (b,a,'parent_child') in all_r): return False
        if rtype == 'parent_child' and ((a,b,'spouse') in all_r or (b,a,'spouse') in all_r): return False
        # 占位节点不参与配偶推导（避免占位↔真人被误推导为配偶）
        if rtype == 'spouse':
            pa = graph.get_person(a)
            pb = graph.get_person(b)
            if (pa and pa.is_placeholder) or (pb and pb.is_placeholder):
                return False
        derived.add(key)
        if rtype in ('spouse','sibling'): derived.add((b,a,rtype))
        return True

    def _gp(cid, rs): return {a for (a,b,t) in rs if b==cid and t=='parent_child'}
    def _gc(pid, rs): return {b for (a,b,t) in rs if a==pid and t=='parent_child'}
    def _gs(pid, rs): return {b for (a,b,t) in rs if a==pid and t=='spouse'}

    queue = deque()
    pp: Set[Tuple[str,str]] = set()  # processed_pairs
    for s in seed_ids:
        if graph.get_person(s): queue.append(s)

    it = 0
    while queue and it < 100:
        it += 1
        batch = set()
        while queue: batch.add(queue.popleft())
        ar = existing | derived
        nr = set()

        for pid in batch:
            p = graph.get_person(pid)
            if not p: continue
            parents = _gp(pid, ar)
            children = _gc(pid, ar)
            spouses = _gs(pid, ar)

            # Rule 1: common parent → siblings
            for par in parents:
                for sib in _gc(par, ar):
                    if sib != pid:
                        pair = tuple(sorted([pid,sib]))
                        if pair not in pp:
                            pp.add(pair)
                            if _add(pid, sib, 'sibling'):
                                nr.add(pid); nr.add(sib)

            # Rule 2: co-parent
            for sp in spouses:
                for ch in children:
                    if _add(sp, ch, 'parent_child'):
                        nr.add(sp); nr.add(ch)

            # Rule 3a: parent perspective → spouse
            for ch in children:
                for op in _gp(ch, ar):
                    if op != pid:
                        pair = tuple(sorted([pid,op]))
                        if pair not in pp:
                            pp.add(pair)
                            pp_set = _gp(pid, ar)
                            op_set = _gp(op, ar)
                            has_pc = (pid,op,'parent_child') in ar or (op,pid,'parent_child') in ar
                            if pid not in op_set and op not in pp_set and not has_pc:
                                if _add(pid, op, 'spouse'):
                                    nr.add(pid); nr.add(op)

            # Rule 3b: child perspective → spouse
            plist = list(parents)
            for i in range(len(plist)):
                for j in range(i+1,len(plist)):
                    a,b = plist[i], plist[j]
                    pair = tuple(sorted([a,b]))
                    if pair not in pp:
                        pp.add(pair)
                        ap,bp = _gp(a,ar), _gp(b,ar)
                        has_pc = (a,b,'parent_child') in ar or (b,a,'parent_child') in ar
                        if a not in bp and b not in ap and not has_pc:
                            if _add(a,b,'spouse'):
                                nr.add(a); nr.add(b)

            # Rule 4: spouse transitivity (must have DIRECT common child in existing)
            for s1 in spouses:
                for s2 in spouses:
                    if s1 != s2:
                        pair = tuple(sorted([s1,s2]))
                        if pair not in pp:
                            pp.add(pair)
                            s1p, s2p = _gp(s1,ar), _gp(s2,ar)
                            has_pc = (s1,s2,'parent_child') in ar or (s2,s1,'parent_child') in ar
                            # Must share a child in EXISTING relationships (not derived)
                            s1k = _gc(s1, existing)
                            s2k = _gc(s2, existing)
                            if s1 not in s2p and s2 not in s1p and not has_pc and (s1k & s2k):
                                if _add(s1,s2,'spouse'):
                                    nr.add(s1); nr.add(s2)

        for nid in nr: queue.append(nid)

    # Write results
    results = []
    written: Set[Tuple[str,str,str]] = set()
    from models import Relationship, RelationshipType
    for (a,b,rtype) in derived:
        nk = (min(a,b),max(a,b),rtype)
        if nk in written: continue
        written.add(nk)
        if any(((r.person1_id==a and r.person2_id==b) or (r.person1_id==b and r.person2_id==a))
               and (_rt(r)==rtype) for r in graph.relationships.values()):
            continue
        try: rt = RelationshipType(rtype)
        except ValueError: rt = RelationshipType.OTHER
        graph.add_relationship(Relationship(a,b,rt))
        p1,p2 = graph.get_person(a), graph.get_person(b)
        results.append({'person_a':p1.name if p1 else a,'person_b':p2.name if p2 else b,'type':rtype,'source':'propagation'})
    return results


def derive_relationships(persons, relationships):
    """兼容旧接口"""
    existing = set()
    for r in relationships:
        a,b,t = r['person_a'],r['person_b'],r['type']
        existing.add((a,b,t)); existing.add((b,a,t))
    new_rels = []
    def add(a,b,rt,src="derived"):
        if a==b: return
        if (a,b,rt) not in existing:
            existing.add((a,b,rt)); existing.add((b,a,rt))
            new_rels.append({"person_a":a,"person_b":b,"type":rt,"source":src})
    parents,children,spouses = {},{},{}
    for r in relationships:
        a,b,t = r['person_a'],r['person_b'],r['type']
        if t=='parent_child':
            parents.setdefault(b,set()).add(a); children.setdefault(a,set()).add(b)
        elif t in ('spouse','夫妻'):
            spouses.setdefault(a,set()).add(b); spouses.setdefault(b,set()).add(a)
    for p,ss in spouses.items():
        for s in ss:
            for c in children.get(p,set()):
                pg,sg = persons.get(p,{}).get('gender','unknown'), persons.get(s,{}).get('gender','unknown')
                if pg=='male' and sg=='female': add(s,c,'parent_child','夫妻推导')
                elif pg=='female' and sg=='male': add(s,c,'parent_child','夫妻推导')
    for c,ps in parents.items():
        for p in ps:
            for s in children.get(p,set()):
                if s!=c: add(c,s,'sibling','同父母推导')
    for c,ps in parents.items():
        pl = list(ps)
        for i in range(len(pl)):
            for j in range(i+1,len(pl)):
                a,b = pl[i],pl[j]
                if a not in children.get(b,set()) and b not in children.get(a,set()):
                    add(a,b,'spouse','共同子女推导')
    return new_rels
