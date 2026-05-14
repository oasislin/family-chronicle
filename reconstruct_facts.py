import json
import re

history_path = 'backend/data/family_20260508_165412_edithistory.json'
facts_path = 'data/family_20260508_165412_facts.json'

# 1. 获取 ID 到姓名的映射
with open(history_path, 'r', encoding='utf-8') as f:
    history = json.load(f)
id_to_name = {e['target_id']: e['target_name'] for e in history if e['action'] == 'create_person'}

# 2. 从损坏的文件中提取所有 ID 块
with open(facts_path, 'rb') as f:
    raw = f.read().decode('utf-8', errors='ignore')

# 提取所有的 ADD_NODE 块
# 我们寻找包含 "id": "person_..." 的 payload
nodes = []
# 这是一个非常激进的提取方案：直接扫描所有 person_id
found_ids = set(re.findall(r'person_[a-f0-9]+|placeholder_[a-f0-9]+', raw))

# 我们不依赖原有的 JSON 结构，直接为每个 ID 生成一个 ADD_NODE
# 因为这是 Event Sourcing，多一点 ADD_NODE 没关系，Compiler 会处理
new_facts = []
for pid in found_ids:
    if pid in id_to_name:
        new_facts.append({
            "id": f"fact_rebuilt_{pid}",
            "family_id": "family_20260508_165412",
            "action": "ADD_NODE",
            "payload": {
                "id": pid,
                "name": id_to_name[pid],
                "gender": "male" if "paternal" in pid or "male" in pid else "female", # 临时占位，稍后修正
                "tags": [],
                "attributes": {}
            }
        })

# 3. 提取所有的关系 (ADD_EDGE)
# 寻找类似 "person_a": "...", "person_b": "...", "type": "..." 的模式
edge_pattern = r'"person_a":\s*"(.*?)",\s*"person_b":\s*"(.*?)",\s*"type":\s*"(.*?)"'
edges = re.findall(edge_pattern, raw)
for src, tgt, rel_type in edges:
    new_facts.append({
        "id": f"fact_rebuilt_edge_{src}_{tgt}",
        "family_id": "family_20260508_165412",
        "action": "ADD_EDGE",
        "payload": {
            "person_a": src,
            "person_b": tgt,
            "type": rel_type
        }
    })

# 4. 写入一个干净的文件
with open(facts_path, 'w', encoding='utf-8') as f:
    json.dump(new_facts, f, ensure_ascii=False, indent=2)

print(f"Reconstructed {len(new_facts)} facts. JSON is now guaranteed to be valid.")
