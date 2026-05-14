
from backend.compiler_engine import CompilerEngine
from backend.fact_store import FactLog
from models import Gender, RelationshipType

def test_biological_slot_logic():
    engine = CompilerEngine(family_id="test_family")
    
    # 1. 初始化林大明和赵春花
    facts = [
        FactLog("test_family", "ADD_NODE", {"id": "daming", "name": "林大明", "gender": "male"}),
        FactLog("test_family", "ADD_NODE", {"id": "chunhua", "name": "赵春花", "gender": "female"}),
        FactLog("test_family", "ADD_EDGE", {"person_a": "daming", "person_b": "chunhua", "type": "spouse"}),
    ]
    
    # 2. 添加林绿洲
    facts.append(FactLog("test_family", "ADD_NODE", {"id": "luzhou", "name": "林绿洲", "gender": "male"}))
    facts.append(FactLog("test_family", "ADD_EDGE", {"person_a": "daming", "person_b": "luzhou", "type": "parent_child"}))
    
    engine.compile(facts)
    print("\n--- Phase 1: Lin Luzhou added with one spouse ---")
    
    # 检查林绿洲的母亲是否被静默关联
    luzhou_parents = engine.parents_of["luzhou"]
    print(f"Luzhou's parents: {[engine.graph.get_person(pid).name for pid in luzhou_parents]}")
    
    # 检查是否为 pending
    luzhou_rels = [r for r in engine.graph.relationships.values() if r.person2_id == "luzhou"]
    for r in luzhou_rels:
        p_name = engine.graph.get_person(r.person1_id).name
        print(f"Relation {p_name} -> Luzhou: biological={r.is_biological}, confirmed={r.is_confirmed}")

    # 3. 添加前妻陈桂芳
    print("\n--- Phase 2: Ex-wife Chen Guifang added ---")
    facts.append(FactLog("test_family", "ADD_NODE", {"id": "guifang", "name": "陈桂芳", "gender": "female"}))
    facts.append(FactLog("test_family", "ADD_EDGE", {"person_a": "daming", "person_b": "guifang", "type": "spouse"}))
    
    engine.compile(facts)
    
    # 检查是否触发了歧义
    print(f"Ambiguities count: {len(engine.ambiguities)}")
    for amb in engine.ambiguities:
        print(f"Ambiguity: {amb['message']}")
        if "candidates" in amb:
            print(f"Candidates: {[c['name'] for c in amb['candidates']]}")

    # 4. 添加林小月
    print("\n--- Phase 3: Lin Xiaoyue added ---")
    facts.append(FactLog("test_family", "ADD_NODE", {"id": "xiaoyue", "name": "林小月", "gender": "female"}))
    facts.append(FactLog("test_family", "ADD_EDGE", {"person_a": "daming", "person_b": "xiaoyue", "type": "parent_child"}))
    
    engine.compile(facts)
    print(f"Ambiguities count after Xiaoyue: {len(engine.ambiguities)}")

    # 5. 显式确认陈桂芳是林小月的母亲
    print("\n--- Phase 4: Explicitly confirming Chen Guifang as Xiaoyue's mother ---")
    # 这里通过添加一个 explicit confirmed edge 来模拟确认动作
    facts.append(FactLog("test_family", "ADD_EDGE", {
        "person_a": "guifang", 
        "person_b": "xiaoyue", 
        "type": "parent_child",
        "attributes": {"is_confirmed": True, "is_biological": True}
    }))
    
    engine.compile(facts)
    
    xiaoyue_rels = [r for r in engine.graph.relationships.values() if r.person2_id == "xiaoyue"]
    for r in xiaoyue_rels:
        p_name = engine.graph.get_person(r.person1_id).name
        print(f"Relation {p_name} -> Xiaoyue: biological={r.is_biological}, confirmed={r.is_confirmed}")

    # 检查关于林小月的母亲歧义是否消失
    remaining_xiaoyue_amb = [a for a in engine.ambiguities if "xiaoyue" in a.get("nodes", [])]
    print(f"Remaining ambiguities for Xiaoyue: {len(remaining_xiaoyue_amb)}")

if __name__ == "__main__":
    test_biological_slot_logic()
