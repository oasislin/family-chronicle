"""
编辑历史记录模块
记录每一次增删改操作，支持按人物/家族/时间筛选。
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


DATA_DIR = Path("data")


def _history_path(family_id: str) -> Path:
    """获取家族历史文件路径"""
    return DATA_DIR / f"{family_id}_edithistory.json"


def load_history(family_id: str) -> List[Dict[str, Any]]:
    """加载家族编辑历史"""
    path = _history_path(family_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history(family_id: str, records: List[Dict[str, Any]]):
    """保存家族编辑历史"""
    path = _history_path(family_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def record_action(
    family_id: str,
    action: str,
    target_type: str,
    target_id: str,
    target_name: str = "",
    before: Any = None,
    after: Any = None,
    summary: str = "",
    actor: str = "user",
):
    """
    记录一次编辑操作。

    Args:
        family_id: 家族 ID
        action: 操作类型 (create_person, update_person, delete_person, merge,
                create_relationship, delete_relationship, auto_import, derive)
        target_type: 目标类型 (person, relationship, event, family)
        target_id: 目标 ID
        target_name: 目标名称（便于阅读）
        before: 修改前状态（创建时为 None）
        after: 修改后状态（删除时为 None）
        summary: 人类可读摘要
        actor: 操作者
    """
    records = load_history(family_id)
    record = {
        "id": f"hist_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "actor": actor,
        "target_type": target_type,
        "target_id": target_id,
        "target_name": target_name,
        "before": before,
        "after": after,
        "summary": summary,
    }
    records.append(record)

    # 只保留最近 1000 条，避免文件过大
    if len(records) > 1000:
        records = records[-1000:]

    save_history(family_id, records)
    return record


def get_person_history(family_id: str, person_id: str) -> List[Dict[str, Any]]:
    """获取某个人物相关的所有编辑历史"""
    records = load_history(family_id)
    return [
        r for r in records
        if r.get("target_id") == person_id
        or (r.get("before") and isinstance(r.get("before"), dict) and r["before"].get("id") == person_id)
        or (r.get("after") and isinstance(r.get("after"), dict) and r["after"].get("id") == person_id)
    ]


def get_recent_history(family_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """获取最近的编辑历史"""
    records = load_history(family_id)
    return records[-limit:]
