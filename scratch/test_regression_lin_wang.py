
import sys
import os
from pathlib import Path

# Add root and backend to path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))
sys.path.append(str(root_dir / "backend"))

from compiler_engine import CompilerEngine
from fact_store import FactLog

def test_regression_lin_wang():
    engine = CompilerEngine("lin_wang_test")
    
    # 我们根据 lin_wang_execution_log.json 中的逻辑提取关键 Fact
    facts = [
        # 1. 林大明 & 赵春花
        FactLog("f1", "ADD_NODE", {"id": "p1", "name": "林大明", "gender": "male"}),
        FactLog("f2", "ADD_NODE", {"id": "p2", "name": "赵春花", "gender": "female"}),
        FactLog("f3", "ADD_EDGE", {"person_a": "p1", "person_b": "p2", "type": "spouse"}),
        
        # 2. 儿子 林绿洲, 林青海
        FactLog("f4", "ADD_NODE", {"id": "p3", "name": "林绿洲", "gender": "male"}),
        FactLog("f5", "ADD_NODE", {"id": "p4", "name": "林青海", "gender": "male"}),
        # 明确指定父母 (模拟 Step 3)
        FactLog("f6", "ADD_EDGE", {"person_a": "p1", "person_b": "p3", "type": "parent_child", "attributes": {"is_confirmed": True}}),
        FactLog("f7", "ADD_EDGE", {"person_a": "p2", "person_b": "p3", "type": "parent_child", "attributes": {"is_confirmed": True}}),
        FactLog("f8", "ADD_EDGE", {"person_a": "p1", "person_b": "p4", "type": "parent_child", "attributes": {"is_confirmed": True}}),
        FactLog("f9", "ADD_EDGE", {"person_a": "p2", "person_b": "p4", "type": "parent_child", "attributes": {"is_confirmed": True}}),
        
        # 4. 前妻 陈桂芳 & 女儿 林小月 (Step 4)
        FactLog("f10", "ADD_NODE", {"id": "p5", "name": "陈桂芳", "gender": "female"}),
        FactLog("f11", "ADD_NODE", {"id": "p6", "name": "林小月", "gender": "female"}),
        FactLog("f12", "ADD_EDGE", {"person_a": "p1", "person_b": "p5", "type": "spouse", "attributes": {"status": "divorced"}}),
        FactLog("f13", "ADD_EDGE", {"person_a": "p1", "person_b": "p6", "type": "parent_child", "attributes": {"is_confirmed": True}}),
        FactLog("f14", "ADD_EDGE", {"person_a": "p5", "person_b": "p6", "type": "parent_child", "attributes": {"is_confirmed": True}}),
        
        # 20. 继妻 刘慧兰 & 儿子 林新生 (模拟后面加入的继妻逻辑)
        FactLog("f15", "ADD_NODE", {"id": "p7", "name": "刘慧兰", "gender": "female"}),
        FactLog("f16", "ADD_NODE", {"id": "p8", "name": "林新生", "gender": "male"}),
        FactLog("f17", "ADD_EDGE", {"person_a": "p1", "person_b": "p7", "type": "spouse"}),
        FactLog("f18", "ADD_EDGE", {"person_a": "p1", "person_b": "p8", "type": "parent_child", "attributes": {"is_confirmed": True}}),
        FactLog("f19", "ADD_EDGE", {"person_a": "p7", "person_b": "p8", "type": "parent_child", "attributes": {"is_confirmed": True}}),
        # 刘慧兰是林绿洲的继母
        FactLog("f20", "ADD_EDGE", {"person_a": "p7", "person_b": "p3", "type": "step_mother"}),
        
        # 爷爷 林建国 (Step 5)
        FactLog("f21", "ADD_NODE", {"id": "p9", "name": "林建国", "gender": "male"}),
        FactLog("f22", "ADD_EDGE", {"person_a": "p9", "person_b": "p1", "type": "parent_child", "attributes": {"is_confirmed": True}})
    ]
    
    graph = engine.compile(facts)
    
    print("\n--- 验证林家血脉 ---")
    
    def check_parents(person_name, expected_bio_parents):
        person = graph.find_person_by_name(person_name)[0]
        parents = engine.parents_of[person.id]
        parent_names = sorted([graph.get_person(pid).name for pid in parents])
        print(f"{person_name} 的生物学父母: {parent_names}")
        assert parent_names == sorted(expected_bio_parents)
        
        step_parents = engine.step_parents_of.get(person.id, set())
        step_names = sorted([graph.get_person(pid).name for pid in step_parents])
        if step_names:
            print(f"{person_name} 的继父母: {step_names}")

    check_parents("林绿洲", ["林大明", "赵春花"])
    check_parents("林青海", ["林大明", "赵春花"])
    check_parents("林小月", ["林大明", "陈桂芳"])
    check_parents("林新生", ["林大明", "刘慧兰"])
    
    # 验证爷爷
    # 爷爷 = 爸爸的爸爸
    l_lz = graph.find_person_by_name("林绿洲")[0]
    fathers = engine._find_candidate_nodes(l_lz.id, "up", "male", biological_only=True)
    grandfathers = []
    for f_id in fathers:
        gfs = engine._find_candidate_nodes(f_id, "up", "male", biological_only=True)
        grandfathers.extend(gfs)
    
    gf_names = [graph.get_person(gid).name for gid in grandfathers]
    print(f"林绿洲的推导爷爷: {gf_names}")
    assert "林建国" in gf_names
    assert len(gf_names) == 1
    
    print("\n✅ 全流程回归测试通过！复杂多配偶情况下的血缘逻辑完全隔离。")

if __name__ == "__main__":
    test_regression_lin_wang()
