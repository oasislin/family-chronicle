"""
家族编年史智能族谱系统 - 数据模型定义
Family Chronicle Intelligent Genealogy System - Data Models

定义核心数据结构，用于存储和处理家族关系数据。
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from enum import Enum


class Gender(Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class EventType(Enum):
    BIRTH = "birth"
    DEATH = "death"
    MARRIAGE = "marriage"
    DIVORCE = "divorce"
    ADOPTION = "adoption"
    ILLNESS = "illness"
    RELOCATION = "relocation"
    EDUCATION = "education"
    CAREER = "career"
    RECOGNITION = "recognition"
    OTHER = "other"


class RelationshipType(Enum):
    PARENT_CHILD = "parent_child"
    SPOUSE = "spouse"
    SIBLING = "sibling"
    GRANDPARENT_GRANDCHILD = "grandparent_grandchild"
    AUNT_UNCLE_NIECE_NEPHEW = "aunt_uncle_niece_nephew"
    COUSIN = "cousin"
    ADOPTED_PARENT_CHILD = "adopted_parent_child"
    GODPARENT_GODCHILD = "godparent_godchild"
    IN_LAW = "in_law"
    OTHER = "other"


class Confidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class DateAccuracy(Enum):
    EXACT = "exact"
    YEAR = "year"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


class Person:
    """家族成员实体"""
    
    def __init__(self, name: str, person_id: str = None, gender: Gender = Gender.UNKNOWN):
        self.id = person_id or f"person_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.gender = gender
        self.birth_date: Optional[str] = None
        self.death_date: Optional[str] = None
        self.birth_place: Optional[str] = None
        self.current_residence: Optional[str] = None
        self.tags: List[str] = []
        self.notes: Optional[str] = None
        self.story: Optional[str] = None
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender.value,
            "birth_date": self.birth_date,
            "death_date": self.death_date,
            "birth_place": self.birth_place,
            "current_residence": self.current_residence,
            "tags": self.tags,
            "notes": self.notes,
            "story": self.story,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Person':
        """从字典创建Person对象"""
        person = cls(
            name=data["name"],
            person_id=data.get("id"),
            gender=Gender(data.get("gender", "unknown"))
        )
        person.birth_date = data.get("birth_date")
        person.death_date = data.get("death_date")
        person.birth_place = data.get("birth_place")
        person.current_residence = data.get("current_residence")
        person.tags = data.get("tags", [])
        person.notes = data.get("notes")
        person.story = data.get("story")
        person.created_at = data.get("created_at", datetime.now().isoformat())
        person.updated_at = data.get("updated_at", person.created_at)
        return person


class Event:
    """家族事件实体"""
    
    def __init__(self, event_type: EventType, description: str, event_id: str = None):
        self.id = event_id or f"event_{uuid.uuid4().hex[:8]}"
        self.type = event_type
        self.description = description
        self.date: Optional[str] = None
        self.date_accuracy: DateAccuracy = DateAccuracy.UNKNOWN
        self.location: Optional[str] = None
        self.participants: List[Dict[str, str]] = []  # [{"person_id": "...", "role": "..."}]
        self.source: Optional[str] = None
        self.confidence: Confidence = Confidence.MEDIUM
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "date": self.date,
            "date_accuracy": self.date_accuracy.value,
            "location": self.location,
            "participants": self.participants,
            "source": self.source,
            "confidence": self.confidence.value,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """从字典创建Event对象"""
        event = cls(
            event_type=EventType(data["type"]),
            description=data["description"],
            event_id=data.get("id")
        )
        event.date = data.get("date")
        event.date_accuracy = DateAccuracy(data.get("date_accuracy", "unknown"))
        event.location = data.get("location")
        event.participants = data.get("participants", [])
        event.source = data.get("source")
        event.confidence = Confidence(data.get("confidence", "medium"))
        event.created_at = data.get("created_at", datetime.now().isoformat())
        return event


class Relationship:
    """家族关系实体"""
    
    def __init__(self, person1_id: str, person2_id: str, 
                 rel_type: RelationshipType, rel_id: str = None):
        self.id = rel_id or f"rel_{uuid.uuid4().hex[:8]}"
        self.person1_id = person1_id
        self.person2_id = person2_id
        self.type = rel_type
        self.subtype: Optional[str] = None
        self.start_date: Optional[str] = None
        self.end_date: Optional[str] = None
        self.attributes: Dict[str, Any] = {}
        self.event_id: Optional[str] = None
        self.notes: Optional[str] = None
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "person1_id": self.person1_id,
            "person2_id": self.person2_id,
            "type": self.type.value,
            "subtype": self.subtype,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "attributes": self.attributes,
            "event_id": self.event_id,
            "notes": self.notes,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """从字典创建Relationship对象"""
        rel = cls(
            person1_id=data["person1_id"],
            person2_id=data["person2_id"],
            rel_type=RelationshipType(data["type"]),
            rel_id=data.get("id")
        )
        rel.subtype = data.get("subtype")
        rel.start_date = data.get("start_date")
        rel.end_date = data.get("end_date")
        rel.attributes = data.get("attributes", {})
        rel.event_id = data.get("event_id")
        rel.notes = data.get("notes")
        rel.created_at = data.get("created_at", datetime.now().isoformat())
        return rel


class FamilyGraph:
    """家族图谱管理类"""
    
    def __init__(self):
        self.people: Dict[str, Person] = {}
        self.events: Dict[str, Event] = {}
        self.relationships: Dict[str, Relationship] = {}
    
    def add_person(self, person: Person) -> str:
        """添加家族成员"""
        self.people[person.id] = person
        return person.id
    
    def add_event(self, event: Event) -> str:
        """添加家族事件"""
        self.events[event.id] = event
        return event.id
    
    def add_relationship(self, relationship: Relationship) -> str:
        """添加家族关系"""
        self.relationships[relationship.id] = relationship
        return relationship.id
    
    def get_person(self, person_id: str) -> Optional[Person]:
        """获取家族成员"""
        return self.people.get(person_id)
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """获取家族事件"""
        return self.events.get(event_id)
    
    def get_relationship(self, rel_id: str) -> Optional[Relationship]:
        """获取家族关系"""
        return self.relationships.get(rel_id)
    
    def find_person_by_name(self, name: str) -> List[Person]:
        """根据姓名查找家族成员"""
        return [p for p in self.people.values() if p.name == name]
    
    def get_person_relationships(self, person_id: str) -> List[Relationship]:
        """获取某人的所有关系"""
        return [r for r in self.relationships.values() 
                if r.person1_id == person_id or r.person2_id == person_id]
    
    def get_person_events(self, person_id: str) -> List[Event]:
        """获取某人参与的所有事件"""
        return [e for e in self.events.values() 
                if any(p["person_id"] == person_id for p in e.participants)]

    def find_ancestors(self, person_id: str, max_depth: int = 10) -> List[Dict[str, Any]]:
        """BFS 查找祖先"""
        ancestors = []
        visited = set()
        queue = [(person_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if depth > max_depth or current_id in visited:
                continue
            visited.add(current_id)

            for rel in self.relationships.values():
                if rel.type == RelationshipType.PARENT_CHILD.value:
                    # person1 是 person2 的父/母
                    if rel.person2_id == current_id and rel.person1_id not in visited:
                        parent = self.get_person(rel.person1_id)
                        if parent:
                            ancestors.append({"person": parent.to_dict(), "generation": depth + 1})
                            queue.append((rel.person1_id, depth + 1))

        return ancestors

    def find_descendants(self, person_id: str, max_depth: int = 10) -> List[Dict[str, Any]]:
        """BFS 查找后代"""
        descendants = []
        visited = set()
        queue = [(person_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if depth > max_depth or current_id in visited:
                continue
            visited.add(current_id)

            for rel in self.relationships.values():
                if rel.type == RelationshipType.PARENT_CHILD.value:
                    # person1 是 person2 的父/母
                    if rel.person1_id == current_id and rel.person2_id not in visited:
                        child = self.get_person(rel.person2_id)
                        if child:
                            descendants.append({"person": child.to_dict(), "generation": depth + 1})
                            queue.append((rel.person2_id, depth + 1))

        return descendants

    def find_shortest_path(self, id1: str, id2: str) -> Optional[Dict[str, Any]]:
        """BFS 查找两人之间的最短路径"""
        if id1 == id2:
            p = self.get_person(id1)
            return {"nodes": [p.to_dict()] if p else [], "relationships": [], "length": 0}

        from collections import deque
        visited = {id1}
        queue = deque([(id1, [id1], [])])

        while queue:
            current_id, path, rels = queue.popleft()

            # 找到所有邻居
            for rel in self.relationships.values():
                neighbor_id = None
                if rel.person1_id == current_id:
                    neighbor_id = rel.person2_id
                elif rel.person2_id == current_id:
                    neighbor_id = rel.person1_id

                if neighbor_id and neighbor_id not in visited:
                    new_path = path + [neighbor_id]
                    new_rels = rels + [rel.to_dict()]

                    if neighbor_id == id2:
                        nodes = [self.get_person(pid).to_dict() for pid in new_path if self.get_person(pid)]
                        return {"nodes": nodes, "relationships": new_rels, "length": len(new_rels)}

                    visited.add(neighbor_id)
                    queue.append((neighbor_id, new_path, new_rels))

        return None

    def get_family_tree(self, root_id: str, max_depth: int = 5) -> Dict[str, Any]:
        """获取以某人为根的家族树"""
        def build_tree(pid, depth, visited):
            if depth > max_depth or pid in visited:
                return None
            visited.add(pid)
            person = self.get_person(pid)
            if not person:
                return None

            node = {"person": person.to_dict(), "children": []}
            for rel in self.relationships.values():
                if rel.type == RelationshipType.PARENT_CHILD.value and rel.person1_id == pid:
                    child_tree = build_tree(rel.person2_id, depth + 1, visited)
                    if child_tree:
                        node["children"].append(child_tree)
            return node

        return build_tree(root_id, 0, set())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "people": [p.to_dict() for p in self.people.values()],
            "events": [e.to_dict() for e in self.events.values()],
            "relationships": [r.to_dict() for r in self.relationships.values()]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FamilyGraph':
        """从字典创建FamilyGraph对象"""
        graph = cls()
        
        for person_data in data.get("people", []):
            person = Person.from_dict(person_data)
            graph.add_person(person)
        
        for event_data in data.get("events", []):
            event = Event.from_dict(event_data)
            graph.add_event(event)
        
        for rel_data in data.get("relationships", []):
            rel = Relationship.from_dict(rel_data)
            graph.add_relationship(rel)
        
        return graph
    
    def export_json(self, filepath: str):
        """导出为JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def import_json(cls, filepath: str) -> 'FamilyGraph':
        """从JSON文件导入"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class AIParserOutput:
    """AI解析输出结构"""
    
    def __init__(self):
        self.entities: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.relationships: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {
            "parsing_confidence": 0.0,
            "ambiguous_references": [],
            "suggested_questions": []
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "entities": self.entities,
            "events": self.events,
            "relationships": self.relationships,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIParserOutput':
        """从字典创建AIParserOutput对象"""
        output = cls()
        output.entities = data.get("entities", [])
        output.events = data.get("events", [])
        output.relationships = data.get("relationships", [])
        output.metadata = data.get("metadata", {})
        return output


def create_sample_data() -> FamilyGraph:
    """创建示例数据"""
    graph = FamilyGraph()
    
    # 创建人物
    grandpa = Person("王大强", gender=Gender.MALE)
    grandpa.birth_date = "1950"
    grandpa.tags = ["长辈", "农民"]
    grandpa.birth_place = "王家村"
    
    father = Person("王建国", gender=Gender.MALE)
    father.birth_date = "1980-12-08"
    father.tags = ["老二", "手艺人", "居住地:县城"]
    father.current_residence = "县城"
    
    mother = Person("李梅", gender=Gender.FEMALE)
    mother.birth_date = "1982"
    mother.tags = ["隔壁村", "二婚"]
    mother.birth_place = "李家村"
    
    godfather = Person("赵大爷", gender=Gender.MALE)
    godfather.birth_date = "1945"
    godfather.tags = ["村长"]
    godfather.birth_place = "赵家村"
    
    daughter = Person("小芳", gender=Gender.FEMALE)
    daughter.birth_date = "1996"
    daughter.tags = ["女儿"]
    
    # 添加人物到图谱
    graph.add_person(grandpa)
    graph.add_person(father)
    graph.add_person(mother)
    graph.add_person(godfather)
    graph.add_person(daughter)
    
    # 创建事件
    marriage_event = Event(EventType.MARRIAGE, "王建国与李梅结婚（二婚）")
    marriage_event.date = "1995-09-15"
    marriage_event.date_accuracy = DateAccuracy.EXACT
    marriage_event.location = "县城"
    marriage_event.participants = [
        {"person_id": father.id, "role": "新郎"},
        {"person_id": mother.id, "role": "新娘"}
    ]
    marriage_event.source = "父亲口述"
    marriage_event.confidence = Confidence.HIGH
    
    adoption_event = Event(EventType.RECOGNITION, "王建国认赵大爷为干爹")
    adoption_event.date = "1996"
    adoption_event.date_accuracy = DateAccuracy.YEAR
    adoption_event.location = "王家村"
    adoption_event.participants = [
        {"person_id": father.id, "role": "干儿子"},
        {"person_id": godfather.id, "role": "干爹"}
    ]
    adoption_event.source = "父亲口述"
    adoption_event.confidence = Confidence.MEDIUM
    
    birth_event = Event(EventType.BIRTH, "小芳出生")
    birth_event.date = "1996"
    birth_event.date_accuracy = DateAccuracy.YEAR
    birth_event.participants = [
        {"person_id": daughter.id, "role": "新生儿"},
        {"person_id": father.id, "role": "父亲"},
        {"person_id": mother.id, "role": "母亲"}
    ]
    birth_event.source = "父亲口述"
    birth_event.confidence = Confidence.HIGH
    
    # 添加事件到图谱
    graph.add_event(marriage_event)
    graph.add_event(adoption_event)
    graph.add_event(birth_event)
    
    # 创建关系
    father_son_rel = Relationship(grandpa.id, father.id, RelationshipType.PARENT_CHILD)
    father_son_rel.subtype = "father"
    father_son_rel.attributes = {"birth_order": "老二"}
    
    marriage_rel = Relationship(father.id, mother.id, RelationshipType.SPOUSE)
    marriage_rel.start_date = "1995-09-15"
    marriage_rel.attributes = {"marriage_number": 2}
    marriage_rel.event_id = marriage_event.id
    
    godfather_rel = Relationship(father.id, godfather.id, RelationshipType.GODPARENT_GODCHILD)
    godfather_rel.subtype = "godfather_godson"
    godfather_rel.start_date = "1996"
    godfather_rel.event_id = adoption_event.id
    
    father_daughter_rel = Relationship(father.id, daughter.id, RelationshipType.PARENT_CHILD)
    father_daughter_rel.subtype = "father"
    father_daughter_rel.event_id = birth_event.id
    
    mother_daughter_rel = Relationship(mother.id, daughter.id, RelationshipType.PARENT_CHILD)
    mother_daughter_rel.subtype = "mother"
    mother_daughter_rel.event_id = birth_event.id
    
    # 添加关系到图谱
    graph.add_relationship(father_son_rel)
    graph.add_relationship(marriage_rel)
    graph.add_relationship(godfather_rel)
    graph.add_relationship(father_daughter_rel)
    graph.add_relationship(mother_daughter_rel)
    
    return graph


if __name__ == "__main__":
    # 创建示例数据
    sample_graph = create_sample_data()
    
    # 导出为JSON
    output_path = "sample_data.json"
    sample_graph.export_json(output_path)
    
    print(f"示例数据已创建并导出到: {output_path}")
    print(f"包含 {len(sample_graph.people)} 个人物")
    print(f"包含 {len(sample_graph.events)} 个事件")
    print(f"包含 {len(sample_graph.relationships)} 个关系")
    
    # 显示王建国的关系
    print("\n王建国的关系:")
    father = sample_graph.find_person_by_name("王建国")[0]
    relationships = sample_graph.get_person_relationships(father.id)
    for rel in relationships:
        other_id = rel.person2_id if rel.person1_id == father.id else rel.person1_id
        other_person = sample_graph.get_person(other_id)
        print(f"  - {other_person.name}: {rel.type.value} ({rel.subtype or '无子类型'})")