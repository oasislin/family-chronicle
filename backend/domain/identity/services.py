"""
身份域服务
"""
from typing import List, Optional
from .entities import Person, Placeholder
from .repositories import PersonRepository

class PersonService:
    """人物服务"""
    
    def __init__(self, repo: PersonRepository):
        self.repo = repo
    
    def create_person(self, name: str, gender: str = "unknown") -> Person:
        """创建新人物"""
        person = Person(id="", name=name, gender=gender)
        return self.repo.save(person)
    
    def create_placeholder(self, name: str, reason: str = "") -> Placeholder:
        """创建占位符"""
        placeholder = Placeholder(name=name, reason=reason)
        return self.repo.save(placeholder)
    
    def get_person(self, person_id: str) -> Optional[Person]:
        """获取人物"""
        return self.repo.get_by_id(person_id)
    
    def find_by_name(self, name: str) -> List[Person]:
        """按姓名查找"""
        return self.repo.get_by_name(name)
    
    def update_person(self, person_id: str, **kwargs) -> Optional[Person]:
        """更新人物信息"""
        person = self.repo.get_by_id(person_id)
        if not person:
            return None
        
        for key, value in kwargs.items():
            if hasattr(person, key):
                setattr(person, key, value)
        
        return self.repo.save(person)
    
    def delete_person(self, person_id: str) -> bool:
        """删除人物"""
        person = self.repo.get_by_id(person_id)
        if not person:
            return False
        
        self.repo.delete(person_id)
        return True
