import uuid
from typing import List, Dict, Any, Tuple
from collections import defaultdict

from models import FamilyGraph, Person, Relationship, RelationshipType, Gender
from fact_store import FactLog
import json
from pathlib import Path

def load_kinship_dictionary() -> dict:
    data_dir = Path(__file__).parent.parent / "data"
    dict_path = data_dir / "kinship_dictionary.json"
    if dict_path.exists():
        with open(dict_path, "r", encoding="utf-8") as f:
            return json.load(f).get("definitions", {})
    return {}

KINSHIP_DICT = load_kinship_dictionary()

class CompilerEngine:
    def __init__(self, family_id: str = ""):
        self.family_id = family_id
        self.graph = FamilyGraph()
        # Fast query indices
        self.parents_of = defaultdict(set)  # child_id -> {parent_ids}
        self.children_of = defaultdict(set) # parent_id -> {child_ids}
        self.spouses_of = defaultdict(set)  # person_id -> {spouse_ids}
        self.new_facts: List[FactLog] = [] # 用于记录本轮产生的 Fact
        self.ambiguities: List[Dict[str, Any]] = [] # 记录推导中的歧义
        self.resolutions: Dict[str, str] = {} # 外部传入的歧义解析方案
        self.rejections: Set[tuple] = set() # 记录被拒绝的关系

    def compile(self, fact_logs: List[FactLog]) -> FamilyGraph:
        """根据事件日志编译出图谱"""
        self.graph = FamilyGraph()
        self.new_facts = []
        
        # 预处理：事实排序，确保原子事实（ADD_NODE 和 原子边）优先于复合关系展开
        # 优先级：ADD_NODE(0) > ADD_EDGE atomic(1) > ADD_EDGE composite(2) > 其他(3)
        def fact_priority(f):
            if f.action == "ADD_NODE": return 0
            if f.action == "ADD_EDGE":
                payload = f.payload or {}
                rel_type = payload.get("type")
                atomic_types = ["parent_child", "spouse", "adopted_parent_child", "godparent_godchild"]
                return 1 if rel_type in atomic_types else 2
            return 3
        
        sorted_facts = sorted(fact_logs, key=fact_priority)

        for fact in sorted_facts:
            self.apply_fact(fact, record=False)
            
        # 后置处理：清理已经由事实解决的歧义
        self.ambiguities = [
            amb for amb in self.ambiguities
            if not self._is_ambiguity_resolved(amb)
        ]
            
        self.validate_graph_constraints()
        return self.graph

    def _is_ambiguity_resolved(self, amb: dict) -> bool:
        """检查歧义是否已经在图谱编译过程中被解决（包括排他性解决）"""
        if amb["type"] == "COUPLED_PARENT_MISSING":
            candidate_parent_id, child_id = amb["nodes"]
            # 1. 直接解决：该候选人确实成为了家长
            if candidate_parent_id in self.parents_of.get(child_id, set()):
                return True
            
            # 2. 排他性解决：该孩子已经有了另一位同性别的家长
            candidate = self.graph.get_person(candidate_parent_id)
            if not candidate: return False
            
            existing_parents = self.parents_of.get(child_id, set())
            for pid in existing_parents:
                p = self.graph.get_person(pid)
                # 如果已经有一个确定的人（非候选人本人）占据了这个性别的家长位置
                if p and p.gender == candidate.gender and pid != candidate_parent_id:
                    return True
                    
        return False

    def apply_fact(self, log: FactLog, record: bool = False):
        if record:
            self.new_facts.append(log)
        action = log.action
        payload = log.payload

        if action == "ADD_NODE":
            person = Person(
                name=payload.get("name"),
                person_id=payload.get("id"),
                gender=Gender(payload.get("gender", "unknown"))
            )
            person.is_placeholder = payload.get("is_placeholder", False)
            person.placeholder_reason = payload.get("placeholder_reason", "")
            person.tags = payload.get("tags", [])
            person.notes = payload.get("notes")
            person.attributes = payload.get("attributes", {})
            self.graph.add_person(person)

        elif action == "REJECT_EDGE":
            # 记录拒绝的关系，防止再次推导
            p1 = payload.get("person_a")
            p2 = payload.get("person_b")
            rel_type = payload.get("type", "parent_child")
            if p1 and p2:
                self.rejections.add(tuple(sorted([p1, p2]) + [rel_type]))

        elif action == "UPDATE_NODE":
            person_id = payload.get("id")
            person = self.graph.get_person(person_id)
            if person:
                if "name" in payload:
                    person.name = payload["name"]
                if "gender" in payload:
                    person.gender = Gender(payload["gender"])
                if "is_placeholder" in payload:
                    person.is_placeholder = payload["is_placeholder"]
                if "tags" in payload:
                    person.tags = payload["tags"]
                if "notes" in payload:
                    person.notes = payload["notes"]
                if "attributes" in payload:
                    person.attributes.update(payload["attributes"])

        elif action == "ADD_EDGE":
            person_a = payload.get("person_a")
            person_b = payload.get("person_b")
            rel_type = payload.get("type")

            # 增加对过继、干亲等非血缘原子关系的直接支持
            atomic_types = ["parent_child", "spouse", "adopted_parent_child", "godparent_godchild"]
            if rel_type in atomic_types:
                self._add_atomic_edge(person_a, person_b, rel_type, payload.get("attributes", {}))
            else:
                self._expand_composite_edge(person_a, person_b, rel_type, record=record)

    def _add_atomic_edge(self, person_a: str, person_b: str, rel_type: str, attributes: dict = None):
        """添加原子关系，并根据拓扑语义触发闭环扩散"""
        # 1. 语义标准化与性别推导
        normalized_type = rel_type
        inferred_gender = None
        if rel_type == "father":
            normalized_type = "parent_child"
            inferred_gender = Gender.MALE
        elif rel_type == "mother":
            normalized_type = "parent_child"
            inferred_gender = Gender.FEMALE
        elif rel_type in ["son", "daughter"]:
            normalized_type = "parent_child"
        elif rel_type == "husband":
            normalized_type = "spouse"
            inferred_gender = Gender.MALE
        elif rel_type == "wife":
            normalized_type = "spouse"
            inferred_gender = Gender.FEMALE

        if inferred_gender:
            p_a = self.graph.get_person(person_a)
            if p_a and p_a.is_placeholder and p_a.gender == Gender.UNKNOWN:
                p_a.gender = inferred_gender

        # 2. 防止重复添加
        if self._edge_exists(person_a, person_b, normalized_type):
            return

        # 3. 创建关系对象
        is_inferred = attributes.get("is_inferred", False) if attributes else False
        rel = Relationship(
            person1_id=person_a,
            person2_id=person_b,
            rel_type=RelationshipType(normalized_type) if normalized_type in [e.value for e in RelationshipType] else RelationshipType.OTHER,
            is_inferred=is_inferred
        )
        if attributes:
            rel.attributes.update(attributes)

        self.graph.add_relationship(rel)
        self._update_indices(rel)

        # 4. 闭环扩散：根据原子类型触发
        if normalized_type == "parent_child":
            p_a = self.graph.get_person(person_a)
            # A 是 B 的家长 -> 检查 A 的所有配偶 S 是否也是 B 的家长
            spouses = self.spouses_of.get(person_a, set())
            for s_id in spouses:
                if s_id not in self.parents_of.get(person_b, set()):
                    self._trigger_parenting_ambiguity(s_id, person_b, person_a)
        
        elif normalized_type == "spouse":
            # A 和 B 是配偶 -> 检查 A 的所有孩子 C，看 B 是否也是 C 的家长
            children_a = self.children_of.get(person_a, set())
            for c_id in children_a:
                if person_b not in self.parents_of.get(c_id, set()):
                    self._trigger_parenting_ambiguity(person_b, c_id, person_a)
            
            # 反向：检查 B 的所有孩子 C，看 A 是否也是 C 的家长
            children_b = self.children_of.get(person_b, set())
            for c_id in children_b:
                if person_a not in self.parents_of.get(c_id, set()):
                    self._trigger_parenting_ambiguity(person_a, c_id, person_b)

    def _trigger_parenting_ambiguity(self, parent_candidate_id: str, child_id: str, known_parent_id: str):
        """生成亲子关系确认（歧义）"""
        # 1. 如果该候选人已经是已知家长，则直接跳过，无需确认
        if parent_candidate_id in self.parents_of.get(child_id, set()):
            return

        # 2. 检查是否已被拒绝
        rejection_key = tuple(sorted([parent_candidate_id, child_id]) + ["parent_child"])
        if rejection_key in self.rejections:
            return

        candidate = self.graph.get_person(parent_candidate_id)
        known = self.graph.get_person(known_parent_id)
        child = self.graph.get_person(child_id)
        
        # --- 自动闭合与冲突拦截逻辑 ---
        existing_parents = self.parents_of.get(child_id, set())
        has_same_gender_parent = False
        for pid in existing_parents:
            p = self.graph.get_person(pid)
            if p and p.gender == candidate.gender and pid != parent_candidate_id:
                has_same_gender_parent = True
                break
        
        # 如果已经有了同性别的家长（例如已知生母），则不再询问其他配偶是否为生母
        if has_same_gender_parent:
            return

        # 如果已知家长 known 只有一个配偶 candidate，且 child 还没有对应性别的家长
        # 则我们认为这是必然关系，直接建立。
        spouses = self.spouses_of.get(known_parent_id, set())
        if len(spouses) == 1 and next(iter(spouses)) == parent_candidate_id:
            # 自动闭合 (标记为推导，不计入永久事实)
            self._add_atomic_edge(parent_candidate_id, child_id, "parent_child", attributes={"is_inferred": True})
            return

        # 如果存在多个配偶或已有竞争家长，则产生歧义建议
        self.ambiguities.append({
            "type": "COUPLED_PARENT_MISSING",
            "nodes": [parent_candidate_id, child_id],
            "message": f"{candidate.name} 是 {known.name} 的配偶，他/她是否也是 {child.name} 的亲生父母？",
            "suggestion": {"action": "ADD_EDGE", "payload": {"person_a": parent_candidate_id, "person_b": child_id, "type": "parent_child"}}
        })
        
    def _update_indices(self, rel: Relationship):
        """更新内部快速查询索引"""
        rt = rel.type.value if hasattr(rel.type, 'value') else str(rel.type)
        if rt == "parent_child":
            self.parents_of[rel.person2_id].add(rel.person1_id)
            self.children_of[rel.person1_id].add(rel.person2_id)
        elif rt == "spouse":
            self.spouses_of[rel.person1_id].add(rel.person2_id)
            self.spouses_of[rel.person2_id].add(rel.person1_id)
        elif rt == "adopted_parent_child":
            self.parents_of[rel.person2_id].add(rel.person1_id)
            self.children_of[rel.person1_id].add(rel.person2_id)
        elif rt == "godparent_godchild":
            # 这里暂时不计入 blood parents 索引，防止干扰生物学推导
            pass

    def _merge_nodes(self, primary_id: str, placeholder_id: str):
        """将占位符节点合并到正式节点"""
        if primary_id == placeholder_id: return
            
        # 1. 迁移所有关系
        rels_to_move = list(self.graph.relationships.values())
        for r in rels_to_move:
            changed = False
            if r.person1_id == placeholder_id:
                r.person1_id = primary_id
                changed = True
            if r.person2_id == placeholder_id:
                r.person2_id = primary_id
                changed = True
            
            if changed:
                # 检查合并后是否产生自环
                if r.person1_id == r.person2_id:
                    if r.id in self.graph.relationships:
                        del self.graph.relationships[r.id]
                # 重新计算索引需要清理旧索引，这里简化为重新生成索引（或者在 apply_fact 结束时整体重建）
                # 暂时手动局部清理
                self._clear_indices_for_node(placeholder_id)
                self._update_indices(r)

        # 2. 删除占位符节点
        if placeholder_id in self.graph.people:
            del self.graph.people[placeholder_id]
        
        # 3. 清理索引
        self._clear_indices_for_node(placeholder_id)

    def _clear_indices_for_node(self, node_id: str):
        """清理特定节点的索引记录"""
        if node_id in self.parents_of: del self.parents_of[node_id]
        if node_id in self.children_of: del self.children_of[node_id]
        if node_id in self.spouses_of: del self.spouses_of[node_id]
        
        for pid in self.parents_of:
            if node_id in self.parents_of[pid]: self.parents_of[pid].remove(node_id)
        for pid in self.children_of:
            if node_id in self.children_of[pid]: self.children_of[pid].remove(node_id)
        for pid in self.spouses_of:
            if node_id in self.spouses_of[pid]: self.spouses_of[pid].remove(node_id)

    def _edge_exists(self, a: str, b: str, rel_type: str) -> bool:
        if rel_type == "parent_child":
            return a in self.parents_of[b]
        elif rel_type == "spouse":
            return b in self.spouses_of[a]
        return False

    def _expand_composite_edge(self, person_a: str, person_b: str, rel_type: str, record: bool = False):
        """展开复合关系词典"""
        # A 是 B 的 rel_type
        definition = KINSHIP_DICT.get(rel_type)
        if not definition:
            print(f"Warning: Unknown composite relationship '{rel_type}' for {person_a} -> {person_b}")
            return
            
        path = definition.get("path", [])
        if not path:
            return

        # 寻路与占位符生成逻辑
        # 维持原逻辑：A 是 B 的 rel_type (例如: A是爷爷, B是孙子)
        # 路径从 B 开始向上寻路，最终应到达 A
        current_id = person_b
        
        for i, step in enumerate(path):
            is_last_step = (i == len(path) - 1)
            direction = step.get("direction")
            expected_gender = step.get("gender")
            is_placeholder = step.get("placeholder", False)
            
            # 确定这一步的目标节点 ID
            if is_last_step:
                target_id = person_a
            else:
                # 在图中寻找是否已经存在符合条件的节点
                candidates = self._find_candidate_nodes(current_id, direction, expected_gender)
                
                # 检查是否有预设的解析方案
                res_key = f"{person_a}_{person_b}_{rel_type}_{i}"
                if res_key in self.resolutions:
                    target_id = self.resolutions[res_key]
                elif len(candidates) == 1:
                    target_id = candidates[0]
                elif len(candidates) > 1:
                    # 记录歧义并中断此路径推导
                    self.ambiguities.append({
                        "key": res_key,
                        "person_a": person_a,
                        "person_b": person_b,
                        "rel_type": rel_type,
                        "step_index": i,
                        "step_label": step.get("label", "未知"),
                        "current_node_id": current_id,
                        "candidates": [
                            {"id": cid, "name": self.graph.get_person(cid).name, "is_placeholder": self.graph.get_person(cid).is_placeholder}
                            for cid in candidates
                        ]
                    })
                    return
                else:
                    # 1. 尝试寻找现有的“中间人” (Look for existing intermediate)
                    # 例如：寻找 A 的孩子 X，且 X 是 B 的家长
                    potential_intermediates = self.children_of.get(person_a, set()) & self.parents_of.get(person_b, set())
                    if potential_intermediates:
                        # 已经有现成的人选了，直接返回
                        return list(potential_intermediates)[0]

                    # 2. 尝试寻找符合性别的现有孩子/家长
                    # 如果是爷爷/孙子，中间人是 A 的儿子/B 的父亲
                    if rel_type in ["grandfather_paternal", "grandfather_maternal", "grandmother_paternal", "grandmother_maternal"]:
                        # 检查 B 是否已经有对应性别的真实家长
                        existing_parents = self.parents_of.get(person_b, set())
                        for pid in existing_parents:
                            p = self.graph.get_person(pid)
                            if p and not p.is_placeholder and p.gender == ("male" if "grandfather" in rel_type else "female"):
                                return pid

                    # 创建占位节点
                    target_id = f"placeholder_{uuid.uuid4().hex[:8]}"
                    p_name = f"{self.graph.get_person(current_id).name}的{step.get('label', '未知')}"
                    self.apply_fact(FactLog(self.family_id, "ADD_NODE", {
                        "id": target_id,
                        "name": p_name,
                        "gender": expected_gender or "unknown",
                        "is_placeholder": True,
                        "placeholder_reason": f"推导 {rel_type} 自动生成"
                    }), record=record)

            # 建立物理链路
            if direction == "up":
                self.apply_fact(FactLog(self.family_id, "ADD_EDGE", {"person_a": target_id, "person_b": current_id, "type": "parent_child"}), record=record)
            elif direction == "down":
                self.apply_fact(FactLog(self.family_id, "ADD_EDGE", {"person_a": current_id, "person_b": target_id, "type": "parent_child"}), record=record)
            elif direction == "horizontal":
                self.apply_fact(FactLog(self.family_id, "ADD_EDGE", {"person_a": current_id, "person_b": target_id, "type": "spouse"}), record=record)
                
            current_id = target_id

    def _find_candidate_nodes(self, current_id: str, direction: str, gender: str) -> List[str]:
        """根据方向和性别查找所有符合条件的节点，并优先返回非占位符节点"""
        if direction == "up":
            candidates = self.parents_of[current_id]
        elif direction == "down":
            candidates = self.children_of[current_id]
        elif direction == "horizontal":
            candidates = self.spouses_of[current_id]
        else:
            return []

        results = []
        for cand_id in candidates:
            p = self.graph.get_person(cand_id)
            # 如果指定了性别，则严格匹配；否则允许匹配 unknown
            if p:
                if not gender or p.gender.value == gender or p.gender.value == "unknown":
                    results.append(cand_id)
        
        # 优化逻辑：如果候选人中既有真实节点又有占位符，优先使用真实节点
        real_nodes = [cid for cid in results if not self.graph.get_person(cid).is_placeholder]
        if real_nodes:
            return real_nodes
            
        return results

    def validate_graph_constraints(self):
        """
        强制性图论约束验证：
        1. 父母唯一性 (最多一父一母，总数不超过2)
        2. 循环引用检测 (禁止 A 是 B 的祖辈同时 B 是 A 的祖辈)
        3. 代际一致性 (禁止捷径冲突：即 A 已经是 B 的祖父/曾祖父，又试图成为 B 的父亲)
        """
        conflicts = []
        
        # 1. 父母唯一性检测
        for child_id, parent_ids in self.parents_of.items():
            if len(parent_ids) > 2:
                child = self.graph.get_person(child_id)
                conflicts.append(f"【超额父母】{child.name} 拥有超过 2 位父母")
                continue
                
            males = []
            females = []
            for pid in parent_ids:
                p = self.graph.get_person(pid)
                if p:
                    if p.gender == Gender.MALE: males.append(p.name)
                    elif p.gender == Gender.FEMALE: females.append(p.name)
            
            if len(males) > 1:
                child = self.graph.get_person(child_id)
                conflicts.append(f"【多父冲突】{child.name} 存在多个男性父亲节点: {', '.join(males)}")
            if len(females) > 1:
                child = self.graph.get_person(child_id)
                conflicts.append(f"【多母冲突】{child.name} 存在多个女性母亲节点: {', '.join(females)}")

        # 2. 拓扑结构检测 (循环与代际跳跃)
        for person_id in self.graph.people:
            # 这里的 ancestors 是不包含直接父母的“上层祖先”
            direct_parents = self.parents_of.get(person_id, set())
            
            # 获取所有祖先（递归向上）
            all_ancestors = self._get_all_ancestors(person_id)
            
            # 循环检测：自己不能是自己的祖先
            if person_id in all_ancestors:
                p = self.graph.get_person(person_id)
                conflicts.append(f"【血缘环路】检测到逻辑闭环：{p.name} 在逻辑上成为了自己的祖先")

            # 代际一致性检测：如果 A 已经是 B 的上层祖先（爷爷及以上），则 A 不能再是 B 的直接父母
            # 这里的 all_ancestors 包含了父母。我们通过路径长度来判断。
            for pid in direct_parents:
                # 检查除了这条直接边，pid 是否还是 person_id 的更远层级的祖先
                # 做法：暂时移除这条边，看看 pid 是否还能到达 person_id 的其他家长
                other_ancestors = set()
                for other_pid in (direct_parents - {pid}):
                    other_ancestors.update(self._get_all_ancestors(other_pid))
                    other_ancestors.add(other_pid)
                
                if pid in other_ancestors:
                    p_node = self.graph.get_person(pid)
                    c_node = self.graph.get_person(person_id)
                    conflicts.append(f"【代际冲突】{p_node.name} 已经是 {c_node.name} 的上层祖辈，不能同时作为直接父母")

        if conflicts:
            raise ValueError("【图谱约束违约】: " + " | ".join(conflicts))

    def _get_all_ancestors(self, person_id: str, visited=None) -> set[str]:
        """递归获取所有祖先节点 ID"""
        if visited is None: visited = set()
        ancestors = set()
        for pid in self.parents_of.get(person_id, []):
            if pid not in visited:
                visited.add(pid)
                ancestors.add(pid)
                ancestors.update(self._get_all_ancestors(pid, visited))
        return ancestors
