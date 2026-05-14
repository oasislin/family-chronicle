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

# 2. 读取文件（按行处理更安全）
# 我们需要先解决之前由于 regex 导致的结构性损坏
# 重新从二进制读取以保证原始性 (虽然已经被我破坏了一次，但我们尽量修复)
with open(facts_path, 'rb') as f:
    content = f.read().decode('utf-8', errors='ignore')

# 3. 针对每一个 ID 进行结构化修复
for pid, name in id_to_name.items():
    # 匹配模式：匹配整个包含 ID 和 Name 的区域
    # 我们知道 ID 之后通常紧跟着 Name 字段
    # 先把之前连在一起的 "林大?gender": "male" 这种结构切开
    content = re.sub(rf'("id":\s*"{pid}",\s*"name":\s*).*?("gender")', rf'\1"{name}",\n      \2', content)

# 4. 修复可能遗漏的逗号和括号
content = content.replace(']  {', '],\n  {')
if not content.endswith(']'):
    content = content.strip()
    if not content.endswith(']'):
        content += '\n]'

# 5. 保存
with open(facts_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Refined repair complete.")
