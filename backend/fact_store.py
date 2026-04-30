import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

class FactLog:
    """事件日志（Fact Log），记录所有对图谱的原子操作"""
    def __init__(self, family_id: str, action: str, payload: Dict[str, Any], fact_id: str = None, timestamp: str = None):
        self.id = fact_id or f"fact_{uuid.uuid4().hex[:12]}"
        self.family_id = family_id
        # action 支持: ADD_NODE, UPDATE_NODE, REMOVE_NODE, ADD_EDGE, REMOVE_EDGE
        self.action = action  
        self.payload = payload
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self):
        return {
            "id": self.id,
            "family_id": self.family_id,
            "action": self.action,
            "payload": self.payload,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            family_id=data.get("family_id"),
            action=data.get("action"),
            payload=data.get("payload", {}),
            fact_id=data.get("id"),
            timestamp=data.get("timestamp")
        )

def get_fact_file_path(family_id: str) -> str:
    """获取指定 family_id 的事件日志文件路径"""
    # 获取 data 目录的绝对路径，确保不依赖工作目录
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    return str(data_dir / f"{family_id}_facts.json")

def load_facts(family_id: str) -> List[FactLog]:
    """加载一个家族的所有事件日志"""
    filepath = get_fact_file_path(family_id)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [FactLog.from_dict(d) for d in data]
    except Exception as e:
        print(f"Error loading facts for {family_id}: {e}")
        return []

def save_facts(family_id: str, facts: List[FactLog]):
    """全量覆盖写入事件日志（通常不直接使用，而是使用 append_facts）"""
    filepath = get_fact_file_path(family_id)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump([fact.to_dict() for fact in facts], f, ensure_ascii=False, indent=2)

def append_fact(family_id: str, fact: FactLog):
    """追加单条事件日志"""
    facts = load_facts(family_id)
    facts.append(fact)
    save_facts(family_id, facts)

def append_facts(family_id: str, new_facts: List[FactLog]):
    """批量追加事件日志"""
    if not new_facts:
        return
    facts = load_facts(family_id)
    facts.extend(new_facts)
    save_facts(family_id, facts)
