
import sys
import os

# 将 backend 路径加入 sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
sys.path.append(os.getcwd())

from backend.compiler_engine import CompilerEngine
from backend.fact_store import FactLog
from models import Gender

def run_test_scenario(name, facts):
    print(f"\n>>> 场景测试: {name}")
    family_id = "test_" + name
    compiler = CompilerEngine(family_id)
    graph = compiler.compile(facts)
    
    rels = []
    for rid, rel in graph.relationships.items():
        p1 = graph.get_person(rel.person1_id)
        p2 = graph.get_person(rel.person2_id)
        rels.append(f"[{rel.type}] {p1.name} -> {p2.name}")
    
    rels.sort()
    for r in rels:
        print(f"  {r}")
        
    placeholders = [p.name for p in graph.people.values() if p.is_placeholder]
    print(f"  占位符: {placeholders}")
    return rels, placeholders

def test_convergence():
    # 场景 A: 先父母，后兄弟
    facts_a = [
        FactLog("f1", "ADD_NODE", {"id": "D", "name": "林大明", "gender": "male"}),
        FactLog("f1", "ADD_NODE", {"id": "Q", "name": "林青海", "gender": "male"}),
        FactLog("f1", "ADD_EDGE", {"person_a": "D", "person_b": "Q", "type": "parent_child"}),
        FactLog("f1", "ADD_NODE", {"id": "L", "name": "林绿洲", "gender": "male"}),
        FactLog("f1", "ADD_EDGE", {"person_a": "L", "person_b": "Q", "type": "brother"})
    ]
    
    # 场景 B: 先兄弟，后父母
    facts_b = [
        FactLog("f2", "ADD_NODE", {"id": "L", "name": "林绿洲", "gender": "male"}),
        FactLog("f2", "ADD_NODE", {"id": "Q", "name": "林青海", "gender": "male"}),
        FactLog("f2", "ADD_EDGE", {"person_a": "L", "person_b": "Q", "type": "brother"}), # 此时应产生占位符
        FactLog("f2", "ADD_NODE", {"id": "D", "name": "林大明", "gender": "male"}),
        FactLog("f2", "ADD_EDGE", {"person_a": "D", "person_b": "Q", "type": "parent_child"}) # 此时应触发合并
    ]
    
    res_a, ph_a = run_test_scenario("先父母后兄弟", facts_a)
    res_b, ph_b = run_test_scenario("先兄弟后父母", facts_b)
    
    print("\n--- 收敛性检查 ---")
    if res_a == res_b and len(ph_a) == len(ph_b) == 0:
        print("SUCCESS: 两种顺序最终结果完全一致，且无冗余占位符！")
    else:
        print("FAILURE: 结果不一致或残留占位符！")
        if res_a != res_b: print(f"关系差异: {set(res_a) ^ set(res_b)}")

if __name__ == "__main__":
    test_convergence()
