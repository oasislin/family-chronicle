import json
import os

history_path = 'backend/data/family_20260508_165412_edithistory.json'
facts_path = 'data/family_20260508_165412_facts.json'

with open(facts_path, 'rb') as f:
    lines = f.read().decode('utf-8', errors='ignore').splitlines()

fixed_lines = []
for line in lines:
    if '"name":' in line:
        # 强制替换整行为标准格式
        fixed_lines.append('      "name": "REPAIR_ME",')
    else:
        fixed_lines.append(line)

repaired = "\n".join(fixed_lines)

# 尝试解析
try:
    data = json.loads(repaired)
    
    with open(history_path, 'r', encoding='utf-8') as hf:
        history = json.load(hf)
    id_to_name = {e['target_id']: e['target_name'] for e in history if e['action'] == 'create_person'}
    
    for fact in data:
        if fact['action'] == 'ADD_NODE':
            pid = fact['payload'].get('id')
            if pid in id_to_name:
                fact['payload']['name'] = id_to_name[pid]
        elif fact['action'] == 'ADD_EDGE':
            # 某些边可能也有 name 属性（虽然目前看没有）
            pass
            
    with open(facts_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Success! Reconstructed with line-by-line method.")
except Exception as e:
    print(f"Line-by-line repair failed: {e}")
    # 打印前 50 行看看
    print("\n".join(fixed_lines[:50]))
