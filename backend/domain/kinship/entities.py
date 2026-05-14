"""
亲属关系域实体
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from uuid import uuid4

@dataclass
class Relationship:
    """亲属关系实体"""
    id: str
    person1_id: str
    person2_id: str
    type: str
    is_biological: bool = False
    is_confirmed: bool = False
    is_inferred: bool = False
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex[:8]

@dataclass
class KinshipPath:
    """亲属关系路径"""
    from_person_id: str
    to_person_id: str
    path: List[Dict[str, Any]]
    relation_type: str
    
    @property
    def length(self) -> int:
        """路径长度"""
        return len(self.path)
