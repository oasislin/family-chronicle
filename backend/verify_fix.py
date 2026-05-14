import sys
import os
from pathlib import Path
from collections import defaultdict

# 确保能导入本地模块 (包含根目录和 backend 目录)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compiler_engine import CompilerEngine
from fact_store import load_facts
from models import Gender

def verify():
    family_id = "family_20260508_165412"
    print(f"正在验证家族: {family_id}")
    
    facts = load_facts(family_id)
    engine = CompilerEngine(family_id)
    engine.compile(facts)
    
    # 1. 验证索引是否包含 wife/husband 关系
    print("\n--- 1. 验证配偶索引 ---")
    # 林建国 (person_87f22351) 的配偶应该是 李玉兰 (person_3cb6133e)
    # 朱雪兰 (person_9dfbcb91) 的配偶应该是 朱世杰 (person_97778c79)
    
    lin_id = "person_87f22351"
    zhu_id = "person_9dfbcb91"
    
    lin_spouses = engine.spouses_of.get(lin_id, set())
    zhu_spouses = engine.spouses_of.get(zhu_id, set())
    
    print(f"林建国的配偶 ID 列表: {lin_spouses}")
    print(f"朱雪兰的配偶 ID 列表: {zhu_spouses}")
    
    for s_id in lin_spouses:
        s = engine.graph.get_person(s_id)
        print(f"检查林建国的配偶: {s.name}, 性别: {s.gender} (类型: {type(s.gender)})")
        print(f"期望性别: {Gender.FEMALE} (类型: {type(Gender.FEMALE)})")
        print(f"匹配结果: {s.gender == Gender.FEMALE}")

    # 2. 验证歧义中的候选人
    print("\n--- 2. 验证推导歧义候选人 ---")
    parenting_ambiguities = [a for a in engine.ambiguities if a.get("type") == "COMPOSITE_PATH_AMBIGUITY"]
    
    for amb in parenting_ambiguities:
        print(f"发现歧义: {amb['message']}")
        candidates = amb.get("candidates", [])
        print(f"候选人列表: {[c['name'] for c in candidates]}")
        if len(candidates) > 0:
            print("✅ 成功：候选人列表中已包含匹配的配偶")
        else:
            print("❌ 失败：候选人列表为空 (这会导致前端提示'无匹配项')")

if __name__ == "__main__":
    verify()
