"""
身份域仓储接口
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import Person

class PersonRepository(ABC):
    """人物仓储接口"""
    
    @abstractmethod
    def save(self, person: Person) -> Person:
        """保存人物"""
        pass
    
    @abstractmethod
    def get_by_id(self, person_id: str) -> Optional[Person]:
        """根据ID获取人物"""
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> List[Person]:
        """根据姓名查找人物"""
        pass
    
    @abstractmethod
    def delete(self, person_id: str) -> None:
        """删除人物"""
        pass
    
    @abstractmethod
    def list_all(self, include_placeholders: bool = True) -> List[Person]:
        """列出所有人"""
        pass
