import json
import os

filepath = 'data/family_20260508_165412_facts.json'

def try_fix():
    # 1. 尝试以 GBK 读取（PowerShell 默认编码）
    try:
        with open(filepath, 'r', encoding='gbk') as f:
            content = f.read()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Success: Converted from GBK to UTF-8")
        return True
    except Exception as e:
        print(f"GBK attempt failed: {e}")
    
    # 2. 尝试以 utf-8-sig 读取
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Success: Converted from UTF-8-SIG to UTF-8")
        return True
    except Exception as e:
        print(f"UTF-8-SIG attempt failed: {e}")
    
    return False

if try_fix():
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Verified: JSON is valid. Total facts: {len(data)}")
    except Exception as e:
        print(f"Verification failed: {e}")
