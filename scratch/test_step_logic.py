
import sys
import os
from pathlib import Path

# Add root and backend to path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))
sys.path.append(str(root_dir / "backend"))

from compiler_engine import CompilerEngine
from fact_store import FactLog
from models import Gender

def test_step_logic():
    engine = CompilerEngine("test_family")
    
    # 1. 基础生物学关系
    facts = [
        FactLog("f1", "ADD_NODE", {"id": "p1", "name": "林大明", "gender": "male"}),
        FactLog("f2", "ADD_NODE", {"id": "p2", "name": "赵春花", "gender": "female"}),
        FactLog("f3", "ADD_NODE", {"id": "p3", "name": "林绿洲", "gender": "male"}),
        FactLog("f4", "ADD_EDGE", {"person_a": "p1", "person_b": "p3", "type": "parent_child", "attributes": {"is_confirmed": True}}), # 林大明是林绿洲的父亲 (Confirmed)
        FactLog("f5", "ADD_EDGE", {"person_a": "p2", "person_b": "p3", "type": "parent_child", "attributes": {"is_confirmed": True}}), # 赵春花是林绿洲的母亲 (Confirmed)
        FactLog("f5b", "ADD_EDGE", {"person_a": "p1", "person_b": "p2", "type": "spouse"}), # 林大明和赵春花是配偶
        
        # 2. 爷爷关系
        FactLog("f6", "ADD_NODE", {"id": "p4", "name": "林建国", "gender": "male"}),
        FactLog("f7", "ADD_EDGE", {"person_a": "p4", "person_b": "p1", "type": "parent_child"}), # 林建国是林大明的父亲
        
        # 3. 继母关系
        FactLog("f8", "ADD_NODE", {"id": "p5", "name": "刘慧兰", "gender": "female"}),
        FactLog("f9", "ADD_EDGE", {"person_a": "p1", "person_b": "p5", "type": "spouse"}),      # 林大明娶了刘慧兰
        FactLog("f10", "ADD_EDGE", {"person_a": "p5", "person_b": "p3", "type": "step_mother"}), # 刘慧兰是林绿洲的继母
        
        # 4. 继母的父亲（不应该是林绿洲的爷爷）
        FactLog("f11", "ADD_NODE", {"id": "p6", "name": "刘老头", "gender": "male"}),
        FactLog("f12", "ADD_EDGE", {"person_a": "p6", "person_b": "p5", "type": "parent_child"}) # 刘老头是刘慧兰的父亲
    ]
    
    graph = engine.compile(facts)
    
    print("\n--- 验证关系 ---")
    # 检查林绿洲的父母
    parents = engine.parents_of["p3"]
    parent_names = [graph.get_person(pid).name for pid in parents]
    print(f"林绿洲的生物学父母: {parent_names}")
    assert "林大明" in parent_names
    assert "赵春花" in parent_names
    assert "刘慧兰" not in parent_names
    
    # 检查林绿洲的继母
    step_parents = engine.step_parents_of.get("p3", set())
    step_parent_names = [graph.get_person(pid).name for pid in step_parents]
    print(f"林绿洲的继父母: {step_parent_names}")
    assert "刘慧兰" in step_parent_names
    
    # 检查推导：林绿洲的爷爷
    # 我们手动触发一次推导，或者检查图中是否已经生成
    print("\n--- 尝试推导爷爷 ---")
    # 爷爷 = 爸爸的爸爸 (biological_only: true)
    grandfather_candidates = engine._find_candidate_nodes("p3", "up", "male", biological_only=True)
    # 第一步：找爸爸
    paternal_candidates = []
    for father_id in grandfather_candidates:
        # 这一步其实 find_candidate_nodes 已经帮我们做了第一层
        pass
    
    # 模拟 _expand_composite_edge 的逻辑
    # 爷爷路径：[up(bio, M), up(bio, M)]
    fathers = engine._find_candidate_nodes("p3", "up", "male", biological_only=True)
    grandfathers = []
    for f_id in fathers:
        gfs = engine._find_candidate_nodes(f_id, "up", "male", biological_only=True)
        grandfathers.extend(gfs)
        
    gf_names = [graph.get_person(gid).name for gid in grandfathers]
    print(f"推导出的爷爷: {gf_names}")
    assert "林建国" in gf_names
    assert "刘老头" not in gf_names
    
    print("\n✅ 测试通过！生物学推导成功拦截了社交路径。")

if __name__ == "__main__":
    test_step_logic()
