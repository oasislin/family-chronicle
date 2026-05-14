import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from fact_store import load_facts, append_facts, FactLog
from compiler_engine import CompilerEngine
from models import FamilyGraph

def load_family_graph(family_id: str) -> FamilyGraph:
    """加载家族图谱数据（基于事件溯源动态编译）"""
    facts = load_facts(family_id)
    engine = CompilerEngine(family_id)
    try:
        if facts:
            engine.compile(facts)
    except ValueError as e:
        logger.error(f"图谱编译逻辑冲突: {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"图谱编译未知错误: {str(e)}")
        raise
    
    return engine.graph

def generate_family_id() -> str:
    """生成唯一家族ID"""
    return f"family_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def _get_rel_type_str(r) -> str:
    """获取关系的类型字符串（兼容Enum和String）"""
    if hasattr(r.type, 'value'):
        return r.type.value
    return str(r.type)

def get_relationship_summary(graph: FamilyGraph, person_id: str) -> str:
    """获取一个人的关系摘要，用于 AI 上下文"""
    rels = []
    for r in graph.relationships.values():
        if r.person1_id == person_id:
            other = graph.get_person(r.person2_id)
            if other:
                rels.append(f"{_get_rel_type_str(r)}:{other.name}")
        elif r.person2_id == person_id:
            other = graph.get_person(r.person1_id)
            if other:
                rels.append(f"{_get_rel_type_str(r)}:{other.name}")
    return ", ".join(rels[:5]) if rels else "无"
