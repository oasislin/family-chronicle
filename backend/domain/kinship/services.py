"""
亲属关系域服务

核心服务，提供统一的亲属关系查询接口，避免重复逻辑和数据不一致问题。
"""
from typing import List, Optional, Dict, Any
from .entities import Relationship, KinshipPath
from .repositories import RelationshipRepository
from ..identity.services import PersonService

# 亲属关系词典
KINSHIP_DICT = {
    "grandmother_maternal": {
        "name": "外婆/外祖母",
        "is_biological": True,
        "path": [
            {"direction": "up", "type": "parent_child", "gender": "female", 
             "label": "母亲", "biological_only": True},
            {"direction": "up", "type": "parent_child", "gender": "female", 
             "label": "外婆", "biological_only": True}
        ]
    },
    "grandfather_maternal": {
        "name": "外公/外祖父",
        "is_biological": True,
        "path": [
            {"direction": "up", "type": "parent_child", "gender": "female", 
             "label": "母亲", "biological_only": True},
            {"direction": "horizontal", "type": "spouse", "gender": "male", 
             "label": "外公"}
        ]
    },
    "grandmother_paternal": {
        "name": "奶奶/祖母",
        "is_biological": True,
        "path": [
            {"direction": "up", "type": "parent_child", "gender": "male", 
             "label": "父亲", "biological_only": True},
            {"direction": "horizontal", "type": "spouse", "gender": "female", 
             "label": "奶奶"}
        ]
    },
    "grandfather_paternal": {
        "name": "爷爷/祖父",
        "is_biological": True,
        "path": [
            {"direction": "up", "type": "parent_child", "gender": "male", 
             "label": "父亲", "biological_only": True},
            {"direction": "up", "type": "parent_child", "gender": "male", 
             "label": "爷爷", "biological_only": True}
        ]
    },
    "mother": {
        "name": "母亲",
        "is_biological": True,
        "path": [
            {"direction": "up", "type": "parent_child", "gender": "female", 
             "label": "母亲", "biological_only": True}
        ]
    },
    "father": {
        "name": "父亲",
        "is_biological": True,
        "path": [
            {"direction": "up", "type": "parent_child", "gender": "male", 
             "label": "父亲", "biological_only": True}
        ]
    },
    "wife": {
        "name": "妻子",
        "is_biological": False,
        "path": [
            {"direction": "horizontal", "type": "spouse", "gender": "female", 
             "label": "妻子"}
        ]
    },
    "husband": {
        "name": "丈夫",
        "is_biological": False,
        "path": [
            {"direction": "horizontal", "type": "spouse", "gender": "male", 
             "label": "丈夫"}
        ]
    }
}

class KinshipService:
    """亲属关系领域服务
    
    提供统一的亲属关系查询和管理接口，所有查询通过仓储进行，
    确保数据一致性，避免重复逻辑。
    """
    
    def __init__(self, repo: RelationshipRepository, person_service: PersonService):
        self.repo = repo
        self.person_service = person_service
    
    def add_relationship(self, person_a_id: str, person_b_id: str, rel_type: str,
                         is_biological: bool = False, is_confirmed: bool = False,
                         is_inferred: bool = False) -> Relationship:
        """建立亲属关系"""
        # 验证人物存在
        person_a = self.person_service.get_person(person_a_id)
        person_b = self.person_service.get_person(person_b_id)
        
        if not person_a or not person_b:
            raise ValueError("人物不存在")
        
        # 创建关系实体
        relationship = Relationship(
            id="",
            person1_id=person_a_id,
            person2_id=person_b_id,
            type=rel_type,
            is_biological=is_biological,
            is_confirmed=is_confirmed,
            is_inferred=is_inferred
        )
        
        return self.repo.save(relationship)
    
    def find_candidates(self, person_id: str, direction: str, 
                        gender: Optional[str] = None, 
                        biological_only: bool = False) -> List[str]:
        """
        查找符合条件的亲属候选人
        
        参数：
            person_id: 目标人物ID
            direction: 'up'=父母, 'down'=子女, 'horizontal'=配偶
            gender: 性别过滤
            biological_only: 是否只查找生物学关系
        
        返回：
            按优先级排序的候选人ID列表：
            1. 已确认的真实节点
            2. 未确认的真实节点
            3. 占位符节点
        """
        # 统一通过仓储查询，确保数据一致性
        candidate_ids = self.repo.find_related(person_id, direction, gender, biological_only)
        
        # 优先级排序
        results = []
        confirmed_results = []
        
        for cand_id in candidate_ids:
            person = self.person_service.get_person(cand_id)
            if not person:
                continue
            
            # 检查关系是否已确认
            if biological_only:
                rels = self.repo.get_person_relationships(person_id)
                for rel in rels:
                    if rel.person1_id == cand_id or rel.person2_id == cand_id:
                        if rel.is_confirmed:
                            confirmed_results.append(cand_id)
                            break
                else:
                    results.append(cand_id)
            else:
                results.append(cand_id)
        
        # 排序：已确认 > 真实节点 > 占位符
        if confirmed_results:
            confirmed_real = [cid for cid in confirmed_results 
                             if not self.person_service.get_person(cid).is_placeholder]
            if confirmed_real:
                return confirmed_real
            return confirmed_results
        
        real_nodes = [cid for cid in results 
                     if not self.person_service.get_person(cid).is_placeholder]
        if real_nodes:
            return real_nodes
        
        return results
    
    def has_relationship(self, person_a_id: str, person_b_id: str, rel_type: str) -> bool:
        """检查两人之间是否存在指定类型的关系"""
        return self.repo.exists(person_a_id, person_b_id, rel_type)
    
    def expand_composite_relationship(self, person_a_id: str, person_b_id: str, 
                                      rel_type: str) -> List[Relationship]:
        """
        展开复合关系为原子关系
        
        参数：
            person_a_id: 关系主体（如外婆）
            person_b_id: 关系客体（如外孙）
            rel_type: 复合关系类型
        
        返回：
            创建的原子关系列表
        """
        definition = KINSHIP_DICT.get(rel_type)
        if not definition:
            raise ValueError(f"未知的复合关系类型: {rel_type}")
        
        path = definition.get("path", [])
        if not path:
            return []
        
        created_rels = []
        current_id = person_b_id  # 从客体开始
        
        for step in path:
            direction = step.get("direction")
            step_type = step.get("type", "parent_child")
            step_gender = step.get("gender")
            biological_only = step.get("biological_only", False)
            
            # 使用统一的查询接口查找候选人
            candidates = self.find_candidates(
                current_id, 
                direction, 
                step_gender, 
                biological_only
            )
            
            if candidates:
                # 优先选择第一个候选人（已按优先级排序）
                target_id = candidates[0]
            else:
                # 创建占位符
                placeholder_name = f"{self.person_service.get_person(current_id).name}的{step.get('label', '未知亲属')}"
                placeholder = self.person_service.create_placeholder(
                    placeholder_name,
                    f"推导 {rel_type} 自动生成"
                )
                target_id = placeholder.id
            
            # 建立关系
            rel = self.add_relationship(
                target_id if direction == "up" else current_id,
                current_id if direction == "up" else target_id,
                step_type,
                is_biological=biological_only,
                is_confirmed=False,
                is_inferred=True
            )
            created_rels.append(rel)
            
            current_id = target_id
        
        return created_rels
    
    def get_person_relationships(self, person_id: str) -> List[Relationship]:
        """获取人物的所有关系"""
        return self.repo.get_person_relationships(person_id)
