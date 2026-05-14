import json
import re

history_path = 'backend/data/family_20260508_165412_edithistory.json'
facts_path = 'data/family_20260508_165412_facts.json'

# 1. 加载映射
with open(history_path, 'r', encoding='utf-8') as f:
    history = json.load(f)

id_to_name = {}
for entry in history:
    if entry['action'] == 'create_person':
        id_to_name[entry['target_id']] = entry['target_name']

# 2. 读取文件并按行修复
new_lines = []
current_id = None

# 以二进制读取并解码，忽略不可见字符
with open(facts_path, 'rb') as f:
    lines = f.read().decode('utf-8', errors='ignore').splitlines()

for line in lines:
    # 查找 ID
    id_match = re.search(r'"id":\s*"(person_[a-f0-9]+|placeholder_[a-f0-9]+)"', line)
    if id_match:
        current_id = id_match.group(1)
        new_lines.append(line)
        continue
    
    # 查找并修复 Name 行
    if '"name":' in line and current_id in id_to_name:
        indent = line[:line.find('"name"')]
        new_lines.append(f'{indent}"name": "{id_to_name[current_id]}",')
        continue
    
    # 其他行保留，但清理非法字符
    new_lines.append(line)

# 3. 结构补齐
content = "\n".join(new_lines)
# 修复可能的 JSON 数组结尾
if not content.strip().endswith(']'):
    content = content.strip()
    if content.endswith('}'):
        content += '\n]'
    elif content.endswith(','):
        content = content[:-1] + '\n]'

with open(facts_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Ultimate repair complete.")
