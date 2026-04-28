
import os
import sys
from pathlib import Path

# 增加路径
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "backend"))

import backend.main as backend_main
backend_main.DATA_DIR = Path(os.getcwd()) / "backend" / "data"

from backend.main import load_family_graph, save_family_graph, _get_rel_type_str
from backend.biography_engine import generate_biography_from_graph
from models import RelationshipType, Gender

def repair_corrupted_graph(family_id):
    print(f"Repairing corrupted graph for {family_id}...")
    graph = load_family_graph(family_id)
    
    bad_rel_ids = [
        "rel_f2d4c8d7", # 赵春花 <-> 陈桂芳 (错误推导的配偶)
        "rel_f87f2c43", # 赵春花 -> 林小月 (错误推导的母女)
        "rel_a5affb8c", # 陈桂芳 -> 林绿洲 (错误推导的母子)
        "rel_5e52f0e4", # 陈桂芳 -> 林青海 (错误推导的母子)
    ]
    
    removed = 0
    for rid in bad_rel_ids:
        if rid in graph.relationships:
            del graph.relationships[rid]
            removed += 1
            print(f"Removed bad relationship: {rid}")

    # 重新生成所有人的传记，清理错误的描述
    for pid in graph.people:
        person = graph.get_person(pid)
        person.story = generate_biography_from_graph(graph, pid)
        print(f"Refreshed bio for {person.name}")

    if removed > 0:
        save_family_graph(family_id, graph)
        print(f"Graph repaired and saved. Removed {removed} relationships.")
    else:
        print("No bad relationships found (already cleaned?).")

if __name__ == "__main__":
    family_id = "family_20260418_175214"
    repair_corrupted_graph(family_id)
