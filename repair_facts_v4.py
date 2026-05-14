import json
import re

history_path = 'backend/data/family_20260508_165412_edithistory.json'
facts_path = 'data/family_20260508_165412_facts.json'

# 1. 尝试以最原始的方式读取
with open(facts_path, 'rb') as f:
    raw = f.read().decode('utf-8', errors='ignore')

# 2. 强行修复结构：找到所有 "name": 后面直到下一个关键字或换行的地方
# 我们把它们统一替换为一个安全的字符串，并补齐引号和逗号
# 匹配 "name": 后面跟着的任何乱七八糟的东西，直到看到 "gender" 或 "is_placeholder" 或换行
repaired = re.sub(r'"name":\s*.*?(?="gender"|"is_placeholder"|\n|\r)', '"name": "REPAIR_ME",\n      ', raw)

# 3. 修复文件头尾
if not repaired.strip().startswith('['): repaired = '[' + repaired
if not repaired.strip().endswith(']'): repaired = repaired.strip().rstrip(',') + '\n]'

# 4. 现在它应该是合法的 JSON 了（或者接近合法）
# 我们尝试解析它并填入真正的名字
try:
    # 稍微清理一下可能多出来的逗号
    repaired = re.sub(r',\s*]', '\n]', repaired)
    data = json.loads(repaired)
    
    # 加载映射
    with open(history_path, 'r', encoding='utf-8') as hf:
        history = json.load(hf)
    id_to_name = {e['target_id']: e['target_name'] for e in history if e['action'] == 'create_person'}
    
    # 填充名字
    for fact in data:
        if fact['action'] == 'ADD_NODE':
            pid = fact['payload'].get('id')
            if pid in id_to_name:
                fact['payload']['name'] = id_to_name[pid]
    
    # 最终保存
    with open(facts_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Success! Fully reconstructed and repaired.")

except Exception as e:
    print(f"Structural repair failed: {e}")
    # 如果还是失败，打印出错位置附近的文本供调试
    match = re.search(r'char (\.+) ', str(e))
    # ... 
