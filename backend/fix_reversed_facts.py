import json
import os

FACTS_FILE = r"c:\SynologyDrive\Project\family-chronicle\data\family_20260418_175214_facts.json"

def fix_reversed_facts():
    if not os.path.exists(FACTS_FILE):
        print(f"File {FACTS_FILE} not found.")
        return

    with open(FACTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    changed = 0
    # 我们知道林大明 (person_b9d996fe) 和 赵春花 (person_d16c25aa) 是父母
    # 林绿洲 (person_d16c25aa) 和 林青海 (person_dc72b2ba) 是儿子
    
    # 修正逻辑：如果 type 是 son/daughter，且 person_a 是父母中的一个，则反转
    parents = {"person_b9d996fe", "person_7d5b9480"} # 赵春花和林大明的ID（需要确认）
    # 等等，我需要确认ID
    # 赵春花: person_b9d996fe
    # 林大明: person_7d5b9480
    # 林绿洲: person_d16c25aa
    # 林青海: person_dc72b2ba
    
    parents = {"person_b9d996fe", "person_7d5b9480"}
    children = {"person_d16c25aa", "person_dc72b2ba"}

    for fact in data:
        payload = fact.get("payload", {})
        rel_type = payload.get("type")
        
        if rel_type in ["son", "daughter"]:
            p1 = payload.get("person_a")
            p2 = payload.get("person_b")
            
            # 如果 A 是已知的父母，且 B 是已知的孩子，那么 A 是 B 的儿子/女儿 是错误的
            # 应该反转
            if p1 in parents and p2 in children:
                payload["person_a"], payload["person_b"] = p2, p1
                changed += 1
                print(f"Reversed Fact {fact['id']}: {p1} -> {p2} (type: {rel_type})")

    if changed > 0:
        with open(FACTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Fixed {changed} reversed facts.")
    else:
        print("No reversed facts found or IDs mismatched.")

if __name__ == "__main__":
    fix_reversed_facts()
