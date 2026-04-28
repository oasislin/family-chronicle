
import os
import sys
from pathlib import Path

# 增加路径
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "backend"))

# 强制设置 DATA_DIR
import backend.main as backend_main
backend_main.DATA_DIR = Path(os.getcwd()) / "backend" / "data"

from backend.main import load_family_graph, save_family_graph, _get_rel_type_str
from backend.biography_engine import generate_biography_from_graph
from models import RelationshipType, Gender

def fix_graph(family_id):
    print(f"Fixing graph for {family_id} in {backend_main.DATA_DIR}...")
    graph = load_family_graph(family_id)
    
    if not graph.people:
        print("Error: Graph has no people. Path might be wrong.")
        return

    changes = 0

    # 1. 修复缺失的 subtype
    for rel in graph.relationships.values():
        if _get_rel_type_str(rel) == "parent_child" and not rel.subtype:
            parent = graph.get_person(rel.person1_id)
            if parent:
                if parent.gender == Gender.MALE:
                    rel.subtype = "father"
                    changes += 1
                    print(f"Fixed subtype for {parent.name} -> child rel to 'father'")
                elif parent.gender == Gender.FEMALE:
                    rel.subtype = "mother"
                    changes += 1
                    print(f"Fixed subtype for {parent.name} -> child rel to 'mother'")
    
    # 2. 重新生成所有人的传记
    for pid in graph.people:
        person = graph.get_person(pid)
        old_story = person.story
        new_story = generate_biography_from_graph(graph, pid)
        if new_story != old_story:
            person.story = new_story
            changes += 1
            print(f"Updated bio for {person.name} ({pid})")

    if changes > 0:
        save_family_graph(family_id, graph)
        print(f"Graph fixed and saved. Total {changes} items updated.")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    family_id = "family_20260418_175214"
    fix_graph(family_id)
