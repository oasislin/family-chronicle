"""
家族编年史智能族谱系统 - 冲突检测引擎
Family Chronicle Intelligent Genealogy System - Conflict Detection Engine

实现三种冲突检测：
- 🟢 无冲突：完美匹配，允许入库
- 🟡 语义模糊：需要用户澄清（如同名人物）
- 🔴 逻辑冲突：数据矛盾，阻断入库
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from models import FamilyGraph, Person, Event, Relationship, EventType, RelationshipType


class ConflictLevel(Enum):
    """冲突级别"""
    NONE = "none"           # 🟢 无冲突
    AMBIGUOUS = "ambiguous" # 🟡 语义模糊
    BLOCKING = "blocking"   # 🔴 逻辑冲突


class ConflictType(Enum):
    """冲突类型枚举"""
    # 人物相关
    DUPLICATE_NAME = "duplicate_name"           # 同名人物存在
    MULTIPLE_MATCHES = "multiple_matches"       # 多个匹配人物
    PERSON_DECEASED = "person_deceased"         # 人物已故
    BIRTH_AFTER_DEATH = "birth_after_death"     # 出生晚于死亡
    BIRTH_IN_FUTURE = "birth_in_future"         # 出生日期在未来
    
    # 关系相关
    RELATIONSHIP_EXISTS = "relationship_exists" # 关系已存在
    SELF_RELATIONSHIP = "self_relationship"     # 自我关系
    DECEASED_NEW_RELATION = "deceased_new_relation"  # 已故人物建立新关系
    INVALID_PARENT_CHILD = "invalid_parent_child"    # 无效的亲子关系
    CIRCULAR_RELATIONSHIP = "circular_relationship"  # 循环关系
    
    # 事件相关
    EVENT_DATE_CONFLICT = "event_date_conflict"     # 事件日期冲突
    PERSON_NOT_BORN = "person_not_born"             # 人物未出生时参与事件
    PERSON_ALREADY_DECEASED = "person_already_deceased"  # 人物已故时参与事件
    
    # 数据质量
    MISSING_REQUIRED = "missing_required"       # 缺少必填字段
    INVALID_DATE_FORMAT = "invalid_date_format" # 日期格式无效


@dataclass
class ConflictItem:
    """冲突项"""
    level: ConflictLevel
    conflict_type: ConflictType
    message: str
    affected_entities: List[str] = field(default_factory=list)  # 涉及的实体ID
    suggestions: List[str] = field(default_factory=list)         # 建议操作
    can_override: bool = False                                   # 是否可强制覆盖
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "type": self.conflict_type.value,
            "message": self.message,
            "affected_entities": self.affected_entities,
            "suggestions": self.suggestions,
            "can_override": self.can_override
        }


@dataclass
class ConflictResult:
    """冲突检测结果"""
    has_conflicts: bool
    has_blocking: bool
    has_ambiguous: bool
    conflicts: List[ConflictItem] = field(default_factory=list)
    warnings: List[ConflictItem] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_conflicts": self.has_conflicts,
            "has_blocking": self.has_blocking,
            "has_ambiguous": self.has_ambiguous,
            "can_proceed": not self.has_blocking,
            "requires_clarification": self.has_ambiguous,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "warnings": [w.to_dict() for w in self.warnings],
            "summary": self._generate_summary()
        }
    
    def _generate_summary(self) -> str:
        """生成摘要"""
        blocking_count = sum(1 for c in self.conflicts if c.level == ConflictLevel.BLOCKING)
        ambiguous_count = sum(1 for c in self.conflicts if c.level == ConflictLevel.AMBIGUOUS)
        warning_count = len(self.warnings)
        
        if blocking_count == 0 and ambiguous_count == 0 and warning_count == 0:
            return "🟢 数据验证通过，无冲突，可直接入库"
        
        parts = []
        if blocking_count > 0:
            parts.append(f"🔴 发现 {blocking_count} 个逻辑冲突，需修正后方可入库")
        if ambiguous_count > 0:
            parts.append(f"🟡 发现 {ambiguous_count} 个语义模糊，需手动确认")
        if warning_count > 0:
            parts.append(f"⚠️ 发现 {warning_count} 个警告")
        
        return "；".join(parts) if parts else "🟢 数据验证通过"


class ConflictDetector:
    """冲突检测引擎"""
    
    def __init__(self, graph: FamilyGraph):
        self.graph = graph
    
    def check_all(self, new_data: Dict[str, Any]) -> ConflictResult:
        """
        执行完整的冲突检测
        
        Args:
            new_data: AI解析输出的数据，包含 entities, events, relationships
        
        Returns:
            ConflictResult: 冲突检测结果
        """
        result = ConflictResult(has_conflicts=False, has_blocking=False, has_ambiguous=False)
        
        # 1. 检测人物冲突
        if "entities" in new_data:
            for entity in new_data["entities"]:
                if entity.get("type") == "person":
                    conflicts = self._check_person(entity)
                    self._merge_results(result, conflicts)
        
        # 2. 检测关系冲突
        if "relationships" in new_data:
            for rel in new_data["relationships"]:
                conflicts = self._check_relationship(rel, new_data.get("entities", []))
                self._merge_results(result, conflicts)
        
        # 3. 检测事件冲突
        if "events" in new_data:
            for event in new_data["events"]:
                conflicts = self._check_event(event, new_data.get("entities", []))
                self._merge_results(result, conflicts)
        
        # 4. 检测交叉引用完整性
        conflicts = self._check_cross_references(new_data)
        self._merge_results(result, conflicts)
        
        return result
    
    def _merge_results(self, target: ConflictResult, source: ConflictResult):
        """合并检测结果"""
        target.conflicts.extend(source.conflicts)
        target.warnings.extend(source.warnings)
        target.has_conflicts = target.has_conflicts or source.has_conflicts
        target.has_blocking = target.has_blocking or source.has_blocking
        target.has_ambiguous = target.has_ambiguous or source.has_ambiguous
    
    def _check_person(self, entity: Dict[str, Any]) -> ConflictResult:
        """检测人物相关冲突"""
        result = ConflictResult(has_conflicts=False, has_blocking=False, has_ambiguous=False)
        
        name = entity.get("name")
        temp_id = entity.get("temp_id")
        
        if not name:
            result.conflicts.append(ConflictItem(
                level=ConflictLevel.BLOCKING,
                conflict_type=ConflictType.MISSING_REQUIRED,
                message="人物缺少姓名字段",
                affected_entities=[temp_id] if temp_id else [],
                suggestions=["请提供人物姓名"]
            ))
            result.has_conflicts = True
            result.has_blocking = True
            return result
        
        # 查找同名人物
        existing = self.graph.find_person_by_name(name)
        
        if len(existing) == 0:
            # 🟢 无冲突 - 新人物
            pass
        elif len(existing) == 1:
            # 🟡 可能是同一个人，需要确认
            existing_person = existing[0]
            
            # 检查是否有足够信息判断是否同一人
            match_score = self._calculate_person_match_score(entity, existing_person)
            
            if match_score >= 0.8:
                # 高度匹配，可能是重复录入
                result.conflicts.append(ConflictItem(
                    level=ConflictLevel.AMBIGUOUS,
                    conflict_type=ConflictType.DUPLICATE_NAME,
                    message=f"人物 '{name}' 已存在于数据库中，高度疑似重复",
                    affected_entities=[existing_person.id, temp_id],
                    suggestions=[
                        f"合并到现有人物: {existing_person.id}",
                        "创建新人物（确认是不同的人）"
                    ],
                    can_override=True
                ))
                result.has_conflicts = True
                result.has_ambiguous = True
            elif match_score >= 0.5:
                # 中等匹配，需要用户判断
                result.warnings.append(ConflictItem(
                    level=ConflictLevel.AMBIGUOUS,
                    conflict_type=ConflictType.DUPLICATE_NAME,
                    message=f"人物 '{name}' 可能与现有记录重复",
                    affected_entities=[existing_person.id, temp_id],
                    suggestions=[
                        "检查是否为同一人",
                        "确认后选择合并或新建"
                    ],
                    can_override=True
                ))
                result.has_conflicts = True
                result.has_ambiguous = True
        else:
            # 🔴 多个同名人物，必须澄清
            result.conflicts.append(ConflictItem(
                level=ConflictLevel.AMBIGUOUS,
                conflict_type=ConflictType.MULTIPLE_MATCHES,
                message=f"数据库中存在 {len(existing)} 个同名人物 '{name}'，请指定具体是哪一个",
                affected_entities=[p.id for p in existing] + [temp_id],
                suggestions=[f"选择: {p.id} ({p.tags})" for p in existing],
                can_override=False
            ))
            result.has_conflicts = True
            result.has_ambiguous = True
        
        # 检查日期合理性
        birth_date = entity.get("birth_date") or entity.get("birth_year")
        death_date = entity.get("death_date") or entity.get("death_year")
        
        if birth_date and death_date:
            if self._compare_dates(birth_date, death_date) > 0:
                result.conflicts.append(ConflictItem(
                    level=ConflictLevel.BLOCKING,
                    conflict_type=ConflictType.BIRTH_AFTER_DEATH,
                    message=f"人物 '{name}' 的出生日期晚于死亡日期",
                    affected_entities=[temp_id],
                    suggestions=["请检查日期是否正确"]
                ))
                result.has_conflicts = True
                result.has_blocking = True
        
        # 检查出生日期是否在未来
        if birth_date and self._is_future_date(birth_date):
            result.conflicts.append(ConflictItem(
                level=ConflictLevel.BLOCKING,
                conflict_type=ConflictType.BIRTH_IN_FUTURE,
                message=f"人物 '{name}' 的出生日期在未来",
                affected_entities=[temp_id],
                suggestions=["请检查日期是否正确"]
            ))
            result.has_conflicts = True
            result.has_blocking = True
        
        return result
    
    def _check_relationship(self, rel: Dict[str, Any], entities: List[Dict]) -> ConflictResult:
        """检测关系相关冲突"""
        result = ConflictResult(has_conflicts=False, has_blocking=False, has_ambiguous=False)
        
        person1_temp_id = rel.get("person1_temp_id") or rel.get("person1_id")
        person2_temp_id = rel.get("person2_temp_id") or rel.get("person2_id")
        rel_type = rel.get("type")
        
        # 解析实际的人物ID（可能是temp_id或real_id）
        person1_id = self._resolve_person_id(person1_temp_id, entities)
        person2_id = self._resolve_person_id(person2_temp_id, entities)
        
        # 检查自我关系
        if person1_id and person2_id and person1_id == person2_id:
            result.conflicts.append(ConflictItem(
                level=ConflictLevel.BLOCKING,
                conflict_type=ConflictType.SELF_RELATIONSHIP,
                message="不能创建人物与自己的关系",
                affected_entities=[person1_temp_id],
                suggestions=["请检查关系定义"]
            ))
            result.has_conflicts = True
            result.has_blocking = True
            return result
        
        # 检查人物是否存在且存活
        for pid, temp_id in [(person1_id, person1_temp_id), (person2_id, person2_temp_id)]:
            if pid:
                person = self.graph.get_person(pid)
                if person and person.death_date:
                    # 已故人物不能建立新关系（除了纪念性关系）
                    if rel_type not in ["memorial", "ancestor"]:
                        result.conflicts.append(ConflictItem(
                            level=ConflictLevel.BLOCKING,
                            conflict_type=ConflictType.DECEASED_NEW_RELATION,
                            message=f"人物 '{person.name}' 已故（{person.death_date}），无法建立新的{rel_type}关系",
                            affected_entities=[pid, temp_id],
                            suggestions=[
                                "确认死亡日期是否正确",
                                "如需记录历史关系，请使用'历史关系'类型"
                            ],
                            can_override=False
                        ))
                        result.has_conflicts = True
                        result.has_blocking = True
        
        # 检查关系是否已存在
        if person1_id and person2_id:
            existing_rels = self._find_existing_relationship(person1_id, person2_id, rel_type)
            if existing_rels:
                result.conflicts.append(ConflictItem(
                    level=ConflictLevel.AMBIGUOUS,
                    conflict_type=ConflictType.RELATIONSHIP_EXISTS,
                    message=f"人物之间的{rel_type}关系已存在",
                    affected_entities=[person1_id, person2_id],
                    suggestions=["合并关系信息", "跳过此关系"],
                    can_override=True
                ))
                result.has_conflicts = True
                result.has_ambiguous = True
        
        # 检查亲子关系的合理性
        if rel_type == "parent_child" and person1_id and person2_id:
            child_result = self._validate_parent_child(person1_id, person2_id, rel, entities)
            result.conflicts.extend(child_result.conflicts)
            result.warnings.extend(child_result.warnings)
            result.has_conflicts = result.has_conflicts or child_result.has_conflicts
            result.has_blocking = result.has_blocking or child_result.has_blocking
            result.has_ambiguous = result.has_ambiguous or child_result.has_ambiguous
        
        return result
    
    def _check_event(self, event: Dict[str, Any], entities: List[Dict]) -> ConflictResult:
        """检测事件相关冲突"""
        result = ConflictResult(has_conflicts=False, has_blocking=False, has_ambiguous=False)
        
        event_type = event.get("type")
        event_date = event.get("date")
        participants = event.get("participants", [])
        
        # 检查事件日期
        if event_date:
            # 检查日期格式
            if not self._is_valid_date_format(event_date):
                result.conflicts.append(ConflictItem(
                    level=ConflictLevel.BLOCKING,
                    conflict_type=ConflictType.INVALID_DATE_FORMAT,
                    message=f"事件日期格式无效: {event_date}",
                    suggestions=["请使用标准日期格式，如: 1990, 1990-01, 1990-01-15"]
                ))
                result.has_conflicts = True
                result.has_blocking = True
        
        # 检查参与者状态
        for participant in participants:
            person_id = participant.get("person_id")
            if not person_id:
                continue
            
            person = self.graph.get_person(person_id)
            if not person:
                continue
            
            # 检查已故人物参与非纪念性事件
            if person.death_date and event_date:
                if self._compare_dates(person.death_date, event_date) < 0:
                    # 死亡日期早于事件日期
                    if event_type not in ["memorial", "ancestor_worship"]:
                        result.conflicts.append(ConflictItem(
                            level=ConflictLevel.BLOCKING,
                            conflict_type=ConflictType.PERSON_ALREADY_DECEASED,
                            message=f"人物 '{person.name}' 已于 {person.death_date} 去世，无法参与 {event_date} 的事件",
                            affected_entities=[person_id],
                            suggestions=[
                                "检查死亡日期是否正确",
                                "检查事件日期是否正确"
                            ]
                        ))
                        result.has_conflicts = True
                        result.has_blocking = True
            
            # 检查未出生人物参与事件
            if person.birth_date and event_date:
                if self._compare_dates(person.birth_date, event_date) > 0:
                    # 出生日期晚于事件日期
                    result.conflicts.append(ConflictItem(
                        level=ConflictLevel.BLOCKING,
                        conflict_type=ConflictType.PERSON_NOT_BORN,
                        message=f"人物 '{person.name}' 出生于 {person.birth_date}，无法参与 {event_date} 的事件",
                        affected_entities=[person_id],
                        suggestions=[
                            "检查出生日期是否正确",
                            "检查事件日期是否正确"
                        ]
                    ))
                    result.has_conflicts = True
                    result.has_blocking = True
        
        return result
    
    def _check_cross_references(self, new_data: Dict[str, Any]) -> ConflictResult:
        """检查交叉引用完整性"""
        result = ConflictResult(has_conflicts=False, has_blocking=False, has_ambiguous=False)
        
        entities = new_data.get("entities", [])
        relationships = new_data.get("relationships", [])
        events = new_data.get("events", [])
        
        # 构建temp_id到实体的映射
        temp_id_map = {e.get("temp_id"): e for e in entities if e.get("temp_id")}
        
        # 检查关系中引用的人物是否存在
        for rel in relationships:
            p1 = rel.get("person1_temp_id")
            p2 = rel.get("person2_temp_id")
            
            if p1 and p1 not in temp_id_map:
                # 检查是否在现有数据库中
                if not self.graph.get_person(p1):
                    result.warnings.append(ConflictItem(
                        level=ConflictLevel.AMBIGUOUS,
                        conflict_type=ConflictType.MISSING_REQUIRED,
                        message=f"关系引用的人物 '{p1}' 既不在新数据中，也不在数据库中",
                        affected_entities=[p1],
                        suggestions=["请确认人物ID是否正确"]
                    ))
                    result.has_conflicts = True
                    result.has_ambiguous = True
            
            if p2 and p2 not in temp_id_map:
                if not self.graph.get_person(p2):
                    result.warnings.append(ConflictItem(
                        level=ConflictLevel.AMBIGUOUS,
                        conflict_type=ConflictType.MISSING_REQUIRED,
                        message=f"关系引用的人物 '{p2}' 既不在新数据中，也不在数据库中",
                        affected_entities=[p2],
                        suggestions=["请确认人物ID是否正确"]
                    ))
                    result.has_conflicts = True
                    result.has_ambiguous = True
        
        return result
    
    def _calculate_person_match_score(self, new_entity: Dict, existing: Person) -> float:
        """计算人物匹配分数 (0-1)"""
        score = 0.0
        checks = 0
        
        # 姓名完全匹配
        if new_entity.get("name") == existing.name:
            score += 0.4
        checks += 0.4
        
        # 性别匹配
        new_gender = new_entity.get("gender")
        if new_gender and existing.gender.value != "unknown":
            if new_gender == existing.gender.value:
                score += 0.2
            checks += 0.2
        
        # 出生日期匹配
        new_birth = new_entity.get("birth_date") or new_entity.get("birth_year")
        if new_birth and existing.birth_date:
            if self._dates_match(new_birth, existing.birth_date):
                score += 0.3
            checks += 0.3
        
        # 标签匹配
        new_tags = set(new_entity.get("tags", []))
        existing_tags = set(existing.tags)
        if new_tags and existing_tags:
            overlap = len(new_tags & existing_tags)
            total = len(new_tags | existing_tags)
            if total > 0:
                score += 0.1 * (overlap / total)
            checks += 0.1
        
        return score / checks if checks > 0 else 0.0
    
    def _find_existing_relationship(self, person1_id: str, person2_id: str, rel_type: str) -> List[Relationship]:
        """查找已存在的关系"""
        matches = []
        for rel in self.graph.relationships.values():
            # 检查双向匹配
            if ((rel.person1_id == person1_id and rel.person2_id == person2_id) or
                (rel.person1_id == person2_id and rel.person2_id == person1_id)):
                if rel.rel_type.value == rel_type or rel_type is None:
                    matches.append(rel)
        return matches
    
    def _validate_parent_child(self, parent_id: str, child_id: str, rel: Dict, entities: List[Dict] = None) -> ConflictResult:
        """验证亲子关系的合理性"""
        result = ConflictResult(has_conflicts=False, has_blocking=False, has_ambiguous=False)
        
        # 从图谱或新数据中获取人物信息
        parent = self.graph.get_person(parent_id)
        child = self.graph.get_person(child_id)
        
        # 如果图谱中没有，尝试从新数据中获取
        parent_birth = None
        child_birth = None
        
        if parent:
            parent_birth = parent.birth_date
        elif entities:
            for e in entities:
                if e.get("temp_id") == parent_id:
                    parent_birth = e.get("birth_date") or e.get("birth_year")
                    break
        
        if child:
            child_birth = child.birth_date
        elif entities:
            for e in entities:
                if e.get("temp_id") == child_id:
                    child_birth = e.get("birth_date") or e.get("birth_year")
                    break
        
        # 检查年龄差异
        if parent_birth and child_birth:
            age_diff = self._calculate_age_difference(parent_birth, child_birth)
            if age_diff is not None:
                parent_name = parent.name if parent else parent_id
                child_name = child.name if child else child_id
                
                if age_diff < 0:
                    result.conflicts.append(ConflictItem(
                        level=ConflictLevel.BLOCKING,
                        conflict_type=ConflictType.INVALID_PARENT_CHILD,
                        message=f"亲子关系异常: 子女 '{child_name}' 的出生日期早于父母 '{parent_name}'",
                        affected_entities=[parent_id, child_id],
                        suggestions=["请检查出生日期"]
                    ))
                    result.has_conflicts = True
                    result.has_blocking = True
                elif age_diff < 12:
                    result.warnings.append(ConflictItem(
                        level=ConflictLevel.AMBIGUOUS,
                        conflict_type=ConflictType.INVALID_PARENT_CHILD,
                        message=f"亲子关系存疑: 父母 '{parent_name}' 与子女 '{child_name}' 仅相差 {age_diff} 岁",
                        affected_entities=[parent_id, child_id],
                        suggestions=["请确认年龄差异是否合理"],
                        can_override=True
                    ))
                    result.has_conflicts = True
                    result.has_ambiguous = True
                elif age_diff > 60:
                    result.warnings.append(ConflictItem(
                        level=ConflictLevel.AMBIGUOUS,
                        conflict_type=ConflictType.INVALID_PARENT_CHILD,
                        message=f"亲子关系存疑: 父母 '{parent_name}' 与子女 '{child_name}' 相差 {age_diff} 岁",
                        affected_entities=[parent_id, child_id],
                        suggestions=["请确认年龄差异是否合理"],
                        can_override=True
                    ))
                    result.has_conflicts = True
                    result.has_ambiguous = True
        
        return result
    
    def _resolve_person_id(self, temp_id: str, entities: List[Dict]) -> Optional[str]:
        """解析人物ID（temp_id或real_id）"""
        if not temp_id:
            return None
        
        # 先检查是否是新数据中的temp_id
        for entity in entities:
            if entity.get("temp_id") == temp_id:
                return temp_id
        
        # 检查是否是数据库中的real_id
        if self.graph.get_person(temp_id):
            return temp_id
        
        return temp_id  # 返回原值，让后续检查处理
    
    def _compare_dates(self, date1: str, date2: str) -> int:
        """
        比较两个日期
        返回: -1 (date1 < date2), 0 (相等), 1 (date1 > date2)
        """
        try:
            d1 = self._parse_date(date1)
            d2 = self._parse_date(date2)
            if d1 < d2:
                return -1
            elif d1 > d2:
                return 1
            return 0
        except:
            return 0
    
    def _parse_date(self, date_str: str) -> datetime:
        """解析日期字符串"""
        date_str = str(date_str).strip()
        
        # 尝试不同格式
        for fmt in ["%Y-%m-%d", "%Y-%m", "%Y"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # 只取年份
        try:
            year = int(date_str[:4])
            return datetime(year, 1, 1)
        except:
            return datetime(1900, 1, 1)
    
    def _is_future_date(self, date_str: str) -> bool:
        """检查日期是否在未来"""
        try:
            d = self._parse_date(date_str)
            return d > datetime.now()
        except:
            return False
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """检查日期格式是否有效"""
        try:
            self._parse_date(date_str)
            return True
        except:
            return False
    
    def _dates_match(self, date1: str, date2: str) -> bool:
        """检查两个日期是否匹配（支持部分匹配，如年份）"""
        try:
            d1 = str(date1).strip()
            d2 = str(date2).strip()
            
            # 完全匹配
            if d1 == d2:
                return True
            
            # 年份匹配
            y1 = d1[:4]
            y2 = d2[:4]
            if y1 == y2:
                return True
            
            return False
        except:
            return False
    
    def _calculate_age_difference(self, date1: str, date2: str) -> Optional[int]:
        """计算两个日期之间的年份差"""
        try:
            d1 = self._parse_date(date1)
            d2 = self._parse_date(date2)
            return abs(d1.year - d2.year)
        except:
            return None


def check_conflicts(graph: FamilyGraph, new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    便捷函数：执行冲突检测
    
    Args:
        graph: 现有的家族图谱
        new_data: 新数据（AI解析输出）
    
    Returns:
        冲突检测结果字典
    """
    detector = ConflictDetector(graph)
    result = detector.check_all(new_data)
    return result.to_dict()


# 测试代码
if __name__ == "__main__":
    # 创建测试数据
    from models import create_sample_data
    
    graph = create_sample_data()
    
    # 测试场景1: 无冲突的新人物
    print("=== 测试场景1: 无冲突的新人物 ===")
    new_data_1 = {
        "entities": [
            {
                "type": "person",
                "name": "张三",
                "temp_id": "temp_person_001",
                "gender": "male",
                "birth_year": "1990",
                "confidence": "high"
            }
        ],
        "events": [],
        "relationships": []
    }
    result_1 = check_conflicts(graph, new_data_1)
    print(json.dumps(result_1, ensure_ascii=False, indent=2))
    
    # 测试场景2: 同名人物（模糊）
    print("\n=== 测试场景2: 同名人物（模糊） ===")
    new_data_2 = {
        "entities": [
            {
                "type": "person",
                "name": "王建国",
                "temp_id": "temp_person_002",
                "gender": "male",
                "confidence": "high"
            }
        ],
        "events": [],
        "relationships": []
    }
    result_2 = check_conflicts(graph, new_data_2)
    print(json.dumps(result_2, ensure_ascii=False, indent=2))
    
    # 测试场景3: 已故人物建立新关系（阻断）
    print("\n=== 测试场景3: 已故人物建立新关系 ===")
    # 先给王大强设置死亡日期
    grandpa_id = None
    for p in graph.people.values():
        if p.name == "王大强":
            p.death_date = "2020"
            grandpa_id = p.id
            break
    
    new_data_3 = {
        "entities": [
            {
                "type": "person",
                "name": "新媳妇",
                "temp_id": "temp_person_003",
                "gender": "female",
                "birth_year": "1995",
                "confidence": "high"
            }
        ],
        "events": [],
        "relationships": [
            {
                "person1_id": grandpa_id,
                "person2_temp_id": "temp_person_003",
                "type": "spouse"
            }
        ]
    }
    result_3 = check_conflicts(graph, new_data_3)
    print(json.dumps(result_3, ensure_ascii=False, indent=2))
    
    # 测试场景4: 亲子关系年龄异常
    print("\n=== 测试场景4: 亲子关系年龄异常 ===")
    new_data_4 = {
        "entities": [
            {
                "type": "person",
                "name": "小明",
                "temp_id": "temp_person_004",
                "gender": "male",
                "birth_year": "2020",
                "confidence": "high"
            },
            {
                "type": "person",
                "name": "小红",
                "temp_id": "temp_person_005",
                "gender": "female",
                "birth_year": "2019",
                "confidence": "high"
            }
        ],
        "events": [],
        "relationships": [
            {
                "person1_temp_id": "temp_person_004",
                "person2_temp_id": "temp_person_005",
                "type": "parent_child"
            }
        ]
    }
    result_4 = check_conflicts(graph, new_data_4)
    print(json.dumps(result_4, ensure_ascii=False, indent=2))
