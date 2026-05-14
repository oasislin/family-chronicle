"""
亲属关系域仓储接口
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import Relationship

class RelationshipRepository(ABC):
    """关系仓储接口"""
    
    @abstractmethod
    def save(self, relationship: Relationship) -> Relationship:
        """保存关系"""
        pass
    
    @abstractmethod
    def get_by_id(self, rel_id: str) -> Optional[Relationship]:
        """根据ID获取关系"""
        pass
    
    @abstractmethod
    def find_related(self, person_id: str, direction: str, 
                     gender: Optional[str] = None, 
                     biological_only: bool = False) -> List[str]:
        """
        查找相关人物
        
        参数：
            person_id: 目标人物ID
            direction: 'up'=父母, 'down'=子女, 'horizontal'=配偶
            gender: 性别过滤
            biological_only: 是否只查找生物学关系
        
        返回：
            相关人物ID列表
        """
        pass
    
    @abstractmethod
    def exists(self, person_a_id: str, person_b_id: str, rel_type: str) -> bool:
        """检查关系是否存在"""
        pass
    
    @abstractmethod
    def delete(self, rel_id: str) -> None:
        """删除关系"""
        pass
    
    @abstractmethod
    def get_person_relationships(self, person_id: str) -> List[Relationship]:
        """获取人物的所有关系"""
        pass
