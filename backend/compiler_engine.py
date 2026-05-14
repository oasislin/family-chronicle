import uuid
from typing import List, Dict, Any, Tuple
from collections import defaultdict

from models import FamilyGraph, Person, Relationship, RelationshipType, Gender
from fact_store import FactLog
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

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
        self.step_parents_of = defaultdict(set) # child_id -> {step_parent_ids}
        self.step_children_of = defaultdict(set) # parent_id -> {step_child_ids}
        self.new_facts: List[FactLog] = [] # 用于记录本轮产生的 Fact
        self.ambiguities: List[Dict[str, Any]] = [] # 记录推导中的歧义
        self.resolutions: Dict[str, str] = {} # 外部传入的歧义解析方案
        self.rejections: Set[tuple] = set() # 记录被拒绝的关系

    def compile(self, fact_logs: List[FactLog]) -> FamilyGraph:
        """
        [Multi-stage Pipeline] 根据事件日志编译出图谱
        """
        # 0. 初始化状态
        self.graph = FamilyGraph()
        self.new_facts = []
        self.ambiguities = []
        self.parents_of = defaultdict(set)
        self.children_of = defaultdict(set)
        self.spouses_of = defaultdict(set)
        self.step_parents_of = defaultdict(set)
        self.step_children_of = defaultdict(set)
        self.rejections = set()
        
        # 1. 阶段一：原始数据加载 (Data Ingestion)
        # 仅负责建立基础节点和索引，不进行任何深层推导
        def fact_priority(f):
            if f.action in ["ADD_NODE", "RESOLVE_AMBIGUITY"]: return 0
            if f.action == "ADD_EDGE":
                payload = f.payload or {}
                rel_type = payload.get("type")
                # 即使是原子关系，也排在节点之后
                return 1 if self._is_atomic_type(rel_type) else 2
            return 3
        
        sorted_facts = sorted(fact_logs, key=fact_priority)
        for fact in sorted_facts:
            self.apply_fact(fact, record=False)

        # 2. 阶段二：逻辑推导 (Logical Inference)
        # 在全量基础关系建立后，统一进行关联发现（如寻找失散的另一半）
        self._run_inference_pass()
            
        # 3. 阶段三：冲突验证与审计 (Constraint Audit)
        try:
            self.validate_graph_constraints()
        except ValueError as e:
            self.ambiguities.append({
                "type": "LOGIC_CONFLICT",
                "key": f"logic_conflict_{uuid.uuid4().hex[:8]}",
                "message": "检测到图谱逻辑冲突，部分事实可能被忽略或导致显示异常。",
                "conflicts": str(e).replace("【图谱约束违约】: ", "").split(" | ")
            })
            
        # 4. 阶段四：状态对齐与清理 (State Reconciliation)
        # 清理已解决的歧义，执行占位符合并
        self.ambiguities = [
            amb for amb in self.ambiguities
            if not self._is_ambiguity_resolved(amb)
        ]
        self._post_process_merges()
        
        # 5. 挂载结果
        self.graph.ambiguities = self.ambiguities
        return self.graph

    def _is_ambiguity_resolved(self, amb: dict) -> bool:
        """检查歧义是否已经在图谱编译过程中被解决（包括排他性解决）"""
        if amb.get("type") == "COUPLED_PARENT_MISSING":
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
        
        if amb.get("type") == "COMPOSITE_PATH_AMBIGUITY":
            key = amb.get("key")
            # 如果该歧义已经有解析方案，则视为已解决
            if key in self.resolutions:
                return True
            
            # 如果该路径指向的人已经通过其他方式确定了（例如已经有了确定的家长）
            person_a = amb.get("person_a")
            rel_type = amb.get("rel_type")
            if person_a and rel_type == "parent_child":
                gender = amb.get("gender_seeking")
                existing_parents = self.parents_of.get(person_a, set())
                for pid in existing_parents:
                    p = self.graph.get_person(pid)
                    if p and p.gender.value == gender:
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
                # 同时也清理已存在的推导边
                existing = self.graph.get_person_relationships(p1)
                for r in existing:
                    if (r.is_inferred and not r.is_confirmed and 
                        ((r.person1_id == p1 and r.person2_id == p2) or (r.person1_id == p2 and r.person2_id == p1)) and
                        r.type.value == rel_type):
                        if r.id in self.graph.relationships:
                            del self.graph.relationships[r.id]
                        self._remove_from_indices(r)

        elif action == "RESOLVE_AMBIGUITY":
            key = payload.get("key")
            target_id = payload.get("target_id")
            if key and target_id:
                self.resolutions[key] = target_id

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

            if self._is_atomic_type(rel_type):
                self._add_atomic_edge(person_a, person_b, rel_type, payload.get("attributes", {}))
            else:
                self._expand_composite_edge(person_a, person_b, rel_type, record=record)

        elif action == "RESOLVE_AMBIGUITY":
            key = payload.get("key")
            target_id = payload.get("target_id")
            if key and target_id:
                self.resolutions[key] = target_id

    def _add_atomic_edge(self, person_a: str, person_b: str, rel_type: str, attributes: dict = None):
        """
        语义协议：A 是 B 的 [rel_type]
        物理映射：根据关系类型决定 A 和 B 谁是 Parent，谁是 Child
        """
        # 1. 语义标准化与物理对齐
        physical_parent = None
        physical_child = None
        normalized_type = "other"
        subject_gender = None # 应用给 person_a (主语)

        if rel_type in ["father", "mother"]:
            normalized_type = "parent_child"
            physical_parent = person_a
            physical_child = person_b
            subject_gender = Gender.MALE if rel_type == "father" else Gender.FEMALE
        elif rel_type in ["son", "daughter"]:
            normalized_type = "parent_child"
            physical_parent = person_b
            physical_child = person_a
            subject_gender = Gender.MALE if rel_type == "son" else Gender.FEMALE
        elif rel_type in ["husband", "wife", "spouse"]:
            normalized_type = "spouse"
            # 对于配偶，物理上 A->B 即可，方向不敏感
            physical_parent = person_a
            physical_child = person_b
            if rel_type == "husband": subject_gender = Gender.MALE
            if rel_type == "wife": subject_gender = Gender.FEMALE
            # 配偶关系不是生物学关系
            attributes = attributes or {}
            attributes["is_biological"] = False
        elif rel_type == "parent_child":
            # 基础降级：默认 A 是 B 的家长
            normalized_type = "parent_child"
            physical_parent = person_a
            physical_child = person_b

        # 应用性别推导给主体 person_a
        p_a = self.graph.get_person(person_a)
        if subject_gender and p_a:
            if p_a.is_placeholder and p_a.gender == Gender.UNKNOWN:
                p_a.gender = subject_gender

        # 处理明确的继亲关系
        is_step = (rel_type in ["step_mother", "step_father", "step_son", "step_daughter", "step_parent_child"])
        if is_step:
            normalized_type = "step_parent_child"
            if rel_type in ["step_mother", "step_father"]:
                physical_parent = person_a
                physical_child = person_b
            elif rel_type in ["step_son", "step_daughter"]:
                physical_parent = person_b
                physical_child = person_a
            elif rel_type == "step_parent_child":
                physical_parent = person_a
                physical_child = person_b
            # 标记为非生物学
            attributes = attributes or {}
            attributes["is_biological"] = False
            attributes["is_confirmed"] = True
        
        # 处理过继和干亲
        if rel_type == "adopted_parent_child":
            normalized_type = "adopted_parent_child"
            physical_parent = person_a
            physical_child = person_b
            attributes = attributes or {}
            attributes["is_biological"] = False
        elif rel_type == "godparent_godchild":
            normalized_type = "godparent_godchild"
            physical_parent = person_a
            physical_child = person_b
            attributes = attributes or {}
            attributes["is_biological"] = False

        # 最终安全检查
        if not physical_parent or not physical_child:
            # 如果依然未确定方向，默认为 A -> B
            physical_parent = person_a
            physical_child = person_b

        # 2. 防止重复添加
        if self._edge_exists(physical_parent, physical_child, normalized_type):
            return

        # 3. 核心：生物学排他性检查 (Strict Biological Exclusivity)
        # 即使在扩散逻辑之外，也要确保手动/AI直接添加的生物学关系不冲突
        attributes = attributes or {}
        is_biological = attributes.get("is_biological", True)
        is_confirmed = attributes.get("is_confirmed", False)

        if normalized_type == "parent_child" and is_biological:
            parent_node = self.graph.get_person(physical_parent)
            if parent_node and parent_node.gender != Gender.UNKNOWN:
                existing_rels = self.graph.get_person_relationships(physical_child)
                for r in existing_rels:
                    if (r.person2_id == physical_child and r.type == RelationshipType.PARENT_CHILD and 
                        r.is_biological and r.person1_id != physical_parent):
                        ep = self.graph.get_person(r.person1_id)
                        if ep and ep.gender == parent_node.gender:
                            # 冲突：如果现有是推导且新的是确定的，替换
                            if not r.is_confirmed and is_confirmed:
                                logger.info(f"排他性替换：移除推导出的{parent_node.gender}家长 {ep.id}，改用确定的 {physical_parent}")
                                if r.id in self.graph.relationships:
                                    del self.graph.relationships[r.id]
                                self._remove_from_indices(r)
                                break
                            elif r.is_confirmed and not is_confirmed:
                                # 现有确定，新的是推导 -> 忽略推导
                                return
                            # 如果两个都是确定的，交由后续冲突检测，此处先通过

        # 4. 创建关系对象
        is_inferred = attributes.get("is_inferred", False) if attributes else False
        is_biological = attributes.get("is_biological", True) if attributes else True
        is_confirmed = attributes.get("is_confirmed", False) if attributes else False

        rel = Relationship(
            person1_id=physical_parent,
            person2_id=physical_child,
            rel_type=RelationshipType(normalized_type) if normalized_type in [e.value for e in RelationshipType] else RelationshipType.OTHER,
            is_inferred=is_inferred,
            is_biological=is_biological,
            is_confirmed=is_confirmed
        )
        if attributes:
            rel.attributes.update(attributes)

        self.graph.add_relationship(rel)
        self._update_indices(rel)
    def _run_inference_pass(self):
        """
        严谨算法：状态收敛循环 (Convergence Loop)
        反复执行推理规则，直到图谱状态不再发生变化。
        """
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            # 记录当前状态指纹
            state_fingerprint = self._get_graph_state_fingerprint()
            
            # 1. 刷新索引
            self._refresh_indices()
            
            # 2. 规则 A：全量亲子关系补全 (Parenting Diffusion)
            self._infer_missing_parents_all()
            
            # 3. 规则 B：性别自动纠偏与推导 (Gender Inference)
            self._infer_missing_genders_all()
            
            # 检查是否收敛
            new_fingerprint = self._get_graph_state_fingerprint()
            if state_fingerprint == new_fingerprint:
                break
                
        if iteration >= max_iterations:
            logger.warning(f"Inference loop reached max iterations ({max_iterations}), potentially non-convergent.")

    def _get_graph_state_fingerprint(self) -> str:
        """生成图谱状态的指纹，用于检测收敛"""
        # 指纹包含：边数量、节点属性摘要、任务数量
        edge_count = len(self.graph.relationships)
        task_count = len(self.ambiguities)
        res_count = len(self.resolutions)
        # 节点性别摘要 (Gender 是推导中最常变动的属性)
        gender_summary = "".join([p.gender.value for p in self.graph.people.values()])
        return f"E:{edge_count}|T:{task_count}|R:{res_count}|G:{gender_summary}"

    def _infer_missing_parents_all(self):
        """规则 A：全量扫描所有孩子，补全缺失的家长"""
        for child_id in list(self.graph.people.keys()):
            # 找到该孩子的所有已知家长
            known_parent_ids = []
            for rel in self.graph.relationships.values():
                if rel.type == RelationshipType.PARENT_CHILD and rel.person2_id == child_id:
                    p = self.graph.get_person(rel.person1_id)
                    if p and p.gender != Gender.UNKNOWN:
                        known_parent_ids.append(p.id)
            
            # 针对每一个已知家长，尝试推导另一位缺失的家长（扩散逻辑）
            for pid in known_parent_ids:
                parent = self.graph.get_person(pid)
                if parent:
                    other_gender = Gender.FEMALE if parent.gender == Gender.MALE else Gender.MALE
                    self._reconcile_parenting_ambiguity(child_id, pid, other_gender)

    def _infer_missing_genders_all(self):
        """规则 B：根据称谓和关系自动推导性别"""
        for p in self.graph.people.values():
            if p.gender == Gender.UNKNOWN:
                # 此处未来可扩展：若他是某人的丈夫 -> MALE，若是某人的妻子 -> FEMALE
                pass

    def _reconcile_parenting_ambiguity(self, child_id: str, known_parent_id: str, gender_seeking: Gender):
        """
        核心推导与排他性对齐：
        确保一个孩子在特定性别（父/母）位上，要么有一个确定的家长，要么由推导引擎维护正确的歧义/推导状态。
        
        遵循两条原则：
        1. 当出现多个选项时，会触发提示
        2. 若系统中该选项已被显性确认，则不再弹出
        """
        child = self.graph.get_person(child_id)
        known = self.graph.get_person(known_parent_id)
        if not child or not known: return

        # 1. 检查锁定状态：是否已有该性别的“确定的”生物学家长
        existing_rels = self.graph.get_person_relationships(child_id)
        confirmed_parent = None
        inferred_rels = []
        
        for r in existing_rels:
            if r.person2_id == child_id and r.type == RelationshipType.PARENT_CHILD and r.is_biological:
                p = self.graph.get_person(r.person1_id)
                if p and p.gender == gender_seeking:
                    if r.is_confirmed:
                        confirmed_parent = p
                    else:
                        inferred_rels.append(r)
        
        if confirmed_parent:
            # 已有确定家长 -> 清理所有相关的推导/歧义
            for r in inferred_rels:
                if r.id in self.graph.relationships:
                    del self.graph.relationships[r.id]
                self._remove_from_indices(r)
            return

        # 2. 收集候选人 (已知家长的所有同性别配偶)
        # 使用统一的查询函数 _find_candidate_nodes，确保查询逻辑一致
        spouse_ids = self._find_candidate_nodes(known_parent_id, "horizontal", gender_seeking.value)
        
        candidates = []
        for s_id in spouse_ids:
            s = self.graph.get_person(s_id)
            if s:
                candidates.append(s)

        amb_key = f"parent_amb_{child_id}_{gender_seeking.value}"
        
        # 0. 检查是否已有解析方案
        if amb_key in self.resolutions:
            res_id = self.resolutions[amb_key]
            if res_id == "REJECTED":
                return
                
            # 如果解析目标在候选人中（或者强制执行），建立确定边
            self._add_atomic_edge(res_id, child_id, "parent_child", attributes={"is_confirmed": True})
            # 清理推导边
            for r in inferred_rels:
                if r.person1_id != res_id:
                    if r.id in self.graph.relationships:
                        del self.graph.relationships[r.id]
                    self._remove_from_indices(r)
            return

        # 3. 根据候选人数量决策
        if len(candidates) == 0:
            # 无候选人 -> 必须提供交互入口，询问是否创建占位符或保持未知
            if not any(a.get("key") == amb_key for a in self.ambiguities):
                target_label = "亲生母亲" if gender_seeking == Gender.FEMALE else "亲生父亲"
                
                self.ambiguities.append({
                    "type": "COUPLED_PARENT_MISSING",
                    "key": amb_key,
                    "person_a": child_id,
                    "rel_type": "parent_child",
                    "gender_seeking": gender_seeking.value,
                    "step_label": target_label,
                    "nodes": [known_parent_id, child_id],
                    "message": f"未找到 {child.name} 的{target_label}。目前仅知其另一位家长为 {known.name}，但其配偶库中无匹配项。是否为此位置创建占位节点？",
                    "questionType": "YES_NO",
                    "candidates": [],
                    "actions": [
                        {
                            "label": "创建新占位节点",
                            "action": "CREATE_PLACEHOLDER",
                            "payload": {"name": f"{child.name}的{target_label}", "gender": gender_seeking.value}
                        },
                        {
                            "label": "暂时忽略",
                            "action": "IGNORE"
                        }
                    ]
                })
            
        elif len(candidates) == 1:
            # 唯一候选人 -> 根据原则：当仅剩一个选项时，直接自动建立关系，无需提示选择
            # 用户之后可在确认阶段选择是否为生物学关系
            target = candidates[0]
            
            # 检查是否已有确认的另一性别的家长
            other_gender = Gender.FEMALE if gender_seeking == Gender.MALE else Gender.MALE
            has_confirmed_other_parent = False
            
            for r in existing_rels:
                if r.person2_id == child_id and r.type == RelationshipType.PARENT_CHILD:
                    p = self.graph.get_person(r.person1_id)
                    if p and p.gender == other_gender and r.is_confirmed and r.is_biological:
                        has_confirmed_other_parent = True
                        break
            
            # 如果已有确认的另一性别家长（如生母已确认），且当前候选人是唯一的配偶，则自动建立确定关系
            if has_confirmed_other_parent:
                self._add_atomic_edge(target.id, child_id, "parent_child", attributes={"is_confirmed": True})
                return
            
            # 唯一候选人情况下，直接建立关系（标记为推导的、生物学的、未确认）
            # 不在此处弹出确认框，而是将确认是否为生物学关系的责任交给前端的确认流程
            self._add_atomic_edge(target.id, child_id, "parent_child", attributes={"is_inferred": True, "is_biological": True, "is_confirmed": False})
            
        else:
            # 多个候选人 -> 交互选择（原则一：多个选项时触发提示）
            if not any(a.get("key") == amb_key for a in self.ambiguities):
                target_label = "亲生母亲" if gender_seeking == Gender.FEMALE else "亲生父亲"
                known_label = "母亲" if known.gender == Gender.FEMALE else ("父亲" if known.gender == Gender.MALE else "家长")
                
                self.ambiguities.append({
                    "type": "COMPOSITE_PATH_AMBIGUITY",
                    "key": amb_key,
                    "person_a": child_id,
                    "rel_type": "parent_child",
                    "gender_seeking": gender_seeking.value,
                    "step_label": target_label,
                    "nodes": [known_parent_id, child_id],
                    "message": f"发现 {child.name} 的{known_label} {known.name} 有多位配偶。请选择谁是 {child.name} 的{target_label}？",
                    "questionType": "CHOICE",
                    "candidates": [{"id": c.id, "name": c.name, "is_placeholder": c.is_placeholder} for c in candidates],
                    "actions": [
                        {
                            "label": f"确认为 {c.name}",
                            "action": "RESOLVE_AMBIGUITY",
                            "target_id": c.id
                        } for c in candidates
                    ] + [
                        {
                            "label": "以上都不是 (创建新占位符)",
                            "action": "CREATE_PLACEHOLDER"
                        }
                    ]
                })


        
    def _is_atomic_type(self, rel_type: str) -> bool:
        """
        判断一个关系类型是否是“原子”的（一步到位）。
        规则：要么在硬编码的基础原子列表里，要么在词典里定义且路径长度为 1。
        """
        base_atomic = ["parent_child", "spouse", "adopted_parent_child", "godparent_godchild", "step_parent_child"]
        if rel_type in base_atomic:
            return True
            
        # 词典驱动判定：如果路径定义只有 1 步，视为原子关系变体（如 wife, father 等）
        definition = KINSHIP_DICT.get(rel_type)
        if definition and len(definition.get("path", [])) == 1:
            return True
            
        # 特殊处理继亲语义变体
        if rel_type in ["step_mother", "step_father", "step_son", "step_daughter"]:
            return True
            
        return False

    def _update_indices(self, rel: Relationship):
        """更新内部快速查询索引"""
        rt = rel.type.value if hasattr(rel.type, 'value') else str(rel.type)
        if rt == "parent_child":
            # 严格约定：rel.person1_id 是家长，rel.person2_id 是孩子
            self.parents_of.setdefault(rel.person2_id, set()).add(rel.person1_id)
            self.children_of.setdefault(rel.person1_id, set()).add(rel.person2_id)
        elif rt == "spouse":
            self.spouses_of[rel.person1_id].add(rel.person2_id)
            self.spouses_of[rel.person2_id].add(rel.person1_id)
        elif rt == "adopted_parent_child":
            self.parents_of[rel.person2_id].add(rel.person1_id)
            self.children_of[rel.person1_id].add(rel.person2_id)
        elif rt == "godparent_godchild":
            # 这里暂时不计入 blood parents 索引，防止干扰生物学推导
            pass
        elif rt == "step_parent_child":
            # 继亲计入专门的索引，不干扰 parents_of (生物学推导)
            self.step_parents_of[rel.person2_id].add(rel.person1_id)

    def _remove_from_indices(self, rel: Relationship):
        """从内部索引中移除关系"""
        rt = rel.type.value if hasattr(rel.type, 'value') else str(rel.type)
        if rt == "parent_child":
            if rel.person2_id in self.parents_of:
                self.parents_of[rel.person2_id].discard(rel.person1_id)
            if rel.person1_id in self.children_of:
                self.children_of[rel.person1_id].discard(rel.person2_id)
        elif rt == "spouse":
            if rel.person1_id in self.spouses_of:
                self.spouses_of[rel.person1_id].discard(rel.person2_id)
            if rel.person2_id in self.spouses_of:
                self.spouses_of[rel.person2_id].discard(rel.person1_id)
        elif rt == "adopted_parent_child":
            if rel.person2_id in self.parents_of:
                self.parents_of[rel.person2_id].discard(rel.person1_id)
            if rel.person1_id in self.children_of:
                self.children_of[rel.person1_id].discard(rel.person2_id)
        elif rt == "step_parent_child":
            if rel.person2_id in self.step_parents_of:
                self.step_parents_of[rel.person2_id].discard(rel.person1_id)
            if rel.person1_id in self.step_children_of:
                self.step_children_of[rel.person1_id].discard(rel.person2_id)

    def _refresh_indices(self):
        """全量重建所有内存索引 (parents_of, children_of, spouses_of, step_parents_of, step_children_of)"""
        self.parents_of = defaultdict(set)
        self.children_of = defaultdict(set)
        self.spouses_of = defaultdict(set)
        self.step_parents_of = defaultdict(set)
        self.step_children_of = defaultdict(set)
        
        for rel in self.graph.relationships.values():
            self._update_indices(rel)

    def _post_process_merges(self):
        """扫描全图，合并逻辑冗余的占位符"""
        placeholders = [p for p in self.graph.people.values() if p.is_placeholder]
        if not placeholders: return
        
        real_people = [p for p in self.graph.people.values() if not p.is_placeholder]
        
        for ph in placeholders:
            ph_children = self.children_of.get(ph.id, set())
            if not ph_children: continue
            
            # 如果占位符的孩子，正好也是某个真实节点的孩子
            for real_p in real_people:
                real_children = self.children_of.get(real_p.id, set())
                # 如果有重合的孩子，且性别相符（或占位符性别未知）
                if ph_children & real_children:
                    if ph.gender == Gender.UNKNOWN or ph.gender == real_p.gender:
                        # 使用 print 替代 logger 以防万一，或者确保 logger 已定义
                        print(f"DEBUG: 检测到冗余占位符 {ph.name}, 自动合并到真实节点 {real_p.name}")
                        self._merge_nodes(real_p.id, ph.id)
                        # 注意：合并后索引已变，需要重新获取占位符列表或跳出当前占位符处理
                        break

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
        
        for pid in list(self.parents_of.keys()):
            if node_id in self.parents_of[pid]: self.parents_of[pid].discard(node_id)
        for pid in list(self.children_of.keys()):
            if node_id in self.children_of[pid]: self.children_of[pid].discard(node_id)
        for pid in list(self.spouses_of.keys()):
            if node_id in self.spouses_of[pid]: self.spouses_of[pid].discard(node_id)
        if node_id in self.step_parents_of: del self.step_parents_of[node_id]
        if node_id in self.step_children_of: del self.step_children_of[node_id]
        for pid in list(self.step_parents_of.keys()):
            if node_id in self.step_parents_of[pid]: self.step_parents_of[pid].discard(node_id)
        for pid in list(self.step_children_of.keys()):
            if node_id in self.step_children_of[pid]: self.step_children_of[pid].discard(node_id)

    def _edge_exists(self, a: str, b: str, rel_type: str) -> bool:
        """检查指定类型的边是否存在（直接从关系图查询，不依赖索引）"""
        rt = rel_type.value if hasattr(rel_type, 'value') else str(rel_type)
        
        for rel in self.graph.relationships.values():
            rel_type_str = rel.type.value if hasattr(rel.type, 'value') else str(rel.type)
            if rel_type_str != rt:
                continue
            
            if (rel.person1_id == a and rel.person2_id == b) or \
               (rel.person1_id == b and rel.person2_id == a):
                return True
        
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
        # 语义：A 是 B 的 rel_type (例如: A是爷爷, B是孙子)
        # 路径起跳点必须是参照点 B (宾语)
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
                biological_only = step.get("biological_only", False)
                candidates = self._find_candidate_nodes(current_id, direction, expected_gender, biological_only=biological_only)
                
                # 检查是否有预设的解析方案
                res_key = f"{person_a}_{person_b}_{rel_type}_{i}"
                if res_key in self.resolutions:
                    target_id = self.resolutions[res_key]
                elif len(candidates) == 1:
                    target_id = candidates[0]
                elif len(candidates) > 1:
                    # 尝试寻找同时也是目标人物对应方向的邻居（Look-ahead 优化）
                    next_step = path[i+1]
                    next_dir = next_step.get("direction")
                    b_to_x_dir = "up" if next_dir == "down" else "down" if next_dir == "up" else "horizontal"
                    
                    target_neighbors = self._find_candidate_nodes(person_b, b_to_x_dir, expected_gender)
                    intersect = set(candidates) & set(target_neighbors)
                    if intersect:
                        target_id = list(intersect)[0]
                    else:
                        self.ambiguities.append({
                            "type": "COMPOSITE_PATH_AMBIGUITY",
                            "key": res_key,
                            "nodes": [person_a, person_b],
                            "message": f"推导 {rel_type} 关系时存在歧义：在 '{step.get('label', '未知')}' 环节发现多个可能的中间人。请指定具体人选：",
                            "person_a": person_a,
                            "person_b": person_b,
                            "rel_type": rel_type,
                            "step_index": i,
                            "step_label": step.get("label", "未知"),
                            "current_node_id": current_id,
                            "questionType": "CHOICE",
                            "candidates": [
                                {"id": cid, "name": self.graph.get_person(cid).name, "is_placeholder": self.graph.get_person(cid).is_placeholder}
                                for cid in candidates
                            ],
                            "actions": [
                                {
                                    "label": f"确认为 {self.graph.get_person(cid).name}",
                                    "action": "RESOLVE_AMBIGUITY",
                                    "target_id": cid
                                } for cid in candidates
                            ] + [
                                {
                                    "label": "以上都不是",
                                    "action": "CREATE_PLACEHOLDER"
                                }
                            ]
                        })
                        return
                else:
                    # --- 核心 Look-ahead 逻辑 (修正版) ---
                    next_step = path[i+1]
                    next_dir = next_step.get("direction")
                    b_to_x_dir = "up" if next_dir == "down" else "down" if next_dir == "up" else "horizontal"
                    
                    b_candidates = self._find_candidate_nodes(person_b, b_to_x_dir, expected_gender)
                    if b_candidates:
                        # 优先从目标 B 的邻居中寻找候选人，实现“相向而行”
                        target_id = b_candidates[0]
                    else:
                        # 最终兜底：只有当双方都没有任何潜在关联人时，才创建占位符
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
            # 核心物理约定：parent_child(A, B) 表示 A 是家长，B 是孩子
            step_type = step.get("type", "parent_child")
            biological_only = step.get("biological_only", False)
            
            if direction == "up":
                # A 寻找家长 X -> 建立 X(家长) -> A(孩子)
                self.apply_fact(FactLog(self.family_id, "ADD_EDGE", {
                    "person_a": target_id,
                    "person_b": current_id,
                    "type": step_type,
                    "attributes": {"is_biological": biological_only, "is_inferred": True, "is_confirmed": False}
                }), record=record)
            elif direction == "down":
                # A 寻找孩子 X -> 建立 A(家长) -> X(孩子)
                self.apply_fact(FactLog(self.family_id, "ADD_EDGE", {
                    "person_a": current_id,
                    "person_b": target_id,
                    "type": step_type,
                    "attributes": {"is_biological": biological_only, "is_inferred": True, "is_confirmed": False}
                }), record=record)
            elif direction == "horizontal":
                self.apply_fact(FactLog(self.family_id, "ADD_EDGE", {
                    "person_a": current_id,
                    "person_b": target_id,
                    "type": step_type,
                    "attributes": {"is_biological": biological_only, "is_inferred": True, "is_confirmed": False}
                }), record=record)
                
            current_id = target_id

    def _find_candidate_nodes(self, current_id: str, direction: str, gender: str, biological_only: bool = False) -> List[str]:
        """
        根据方向和性别查找所有符合条件的节点（直接从关系图查询，不依赖索引）
        
        参数：
            current_id: 当前节点ID
            direction: 查找方向 ('up'=父母, 'down'=子女, 'horizontal'=配偶)
            gender: 期望性别过滤
            biological_only: 是否只查找生物学关系
        
        返回：
            按优先级排序的候选人ID列表：
            1. 已确认的真实节点
            2. 未确认的真实节点
            3. 占位符节点
        """
        candidates = set()
        
        # 直接从关系图查询，不依赖索引
        for rel in self.graph.relationships.values():
            rel_type = rel.type.value if hasattr(rel.type, 'value') else str(rel.type)
            
            # 处理父母关系
            if direction == "up" and rel_type == "parent_child":
                if rel.person2_id == current_id:  # current_id 是孩子
                    # 检查是否是继亲
                    if biological_only:
                        if rel.is_biological:
                            candidates.add(rel.person1_id)
                    else:
                        candidates.add(rel.person1_id)
            
            # 处理子女关系
            elif direction == "down" and rel_type == "parent_child":
                if rel.person1_id == current_id:  # current_id 是父母
                    if biological_only:
                        if rel.is_biological:
                            candidates.add(rel.person2_id)
                    else:
                        candidates.add(rel.person2_id)
            
            # 处理配偶关系
            elif direction == "horizontal" and rel_type == "spouse":
                if rel.person1_id == current_id:
                    candidates.add(rel.person2_id)
                elif rel.person2_id == current_id:
                    candidates.add(rel.person1_id)

        results = []
        confirmed_results = []  # 已确认的关系
        
        for cand_id in candidates:
            p = self.graph.get_person(cand_id)
            if not p:
                continue
                
            # 过滤性别
            if gender and p.gender.value != gender and p.gender.value != "unknown":
                continue
            
            # 如果需要生物学过滤，再次确认
            if biological_only:
                is_bio = False
                is_confirmed = False
                for r in self.graph.relationships.values():
                    if ((r.person1_id == cand_id and r.person2_id == current_id) or 
                        (r.person1_id == current_id and r.person2_id == cand_id)):
                        if r.is_biological:
                            is_bio = True
                        if r.is_confirmed:
                            is_confirmed = True
                        break
                if not is_bio: 
                    continue
                
                # 已确认的生物学关系优先
                if is_confirmed:
                    confirmed_results.append(cand_id)
                    continue
            
            results.append(cand_id)
        
        # 优先级排序：
        # 1. 已确认的关系
        # 2. 真实节点（非占位符）
        # 3. 占位符
        
        # 先处理已确认的结果
        if confirmed_results:
            # 从已确认结果中优先选择非占位符
            confirmed_real = [cid for cid in confirmed_results if not self.graph.get_person(cid).is_placeholder]
            if confirmed_real:
                return confirmed_real
            return confirmed_results
        
        # 再处理普通结果
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
