import json
import re

history_path = 'backend/data/family_20260508_165412_edithistory.json'
facts_path = 'data/family_20260508_165412_facts.json'

# 1. 加载 ID 到 姓名的映射
with open(history_path, 'r', encoding='utf-8') as f:
    history = json.load(f)

id_to_name = {}
for entry in history:
    if entry['action'] == 'create_person':
        id_to_name[entry['target_id']] = entry['target_name']

print(f"Loaded {len(id_to_name)} ID-to-Name mappings.")

# 2. 读取损坏的 facts 文件（尝试用 gbk 忽略错误读取，或者按行处理）
with open(facts_path, 'rb') as f:
    raw_content = f.read().decode('gbk', errors='ignore')

# 3. 修复逻辑：
# 我们需要找到类似 "id": "person_c395d75d",\n      "name": "..." 的结构
# 或者直接全局替换，因为 ID 是唯一的
for pid, name in id_to_name.items():
    # 匹配模式： "id": "pid",\s+"name": "[^"]+"
    pattern = rf'("id":\s*"{pid}",\s*"name":\s*")[^"]+(")'
    raw_content = re.sub(pattern, rf'\1{name}\2', raw_content)

# 4. 修复文件结尾和整体结构
# 确保文件以 ] 结尾，移除可能存在的中间闭合
raw_content = raw_content.split(']')[0] + ']'

# 5. 保存
with open(facts_path, 'w', encoding='utf-8') as f:
    f.write(raw_content)

print("Repair complete. Facts file restored.")
