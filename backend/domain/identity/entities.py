"""
身份域实体 - 人物和占位符
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from uuid import uuid4

@dataclass
class Person:
    """人物实体"""
    id: str
    name: str
    gender: str = "unknown"
    is_placeholder: bool = False
    placeholder_reason: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex[:8]

@dataclass
class Placeholder(Person):
    """占位符实体 - 用于表示尚未确认的人物"""
    def __init__(self, name: str, reason: str = ""):
        super().__init__(
            id="",
            name=name,
            is_placeholder=True,
            placeholder_reason=reason
        )
