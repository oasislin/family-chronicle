import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api"
FAMILY_ID = "smoke_test_family"

def test_smoke():
    print("=== 1. 测试 AI 提取 (Chat Extract) ===")
    extract_data = {
        "text": "林大明和妻子赵春花生了个儿子叫林绿洲",
        "family_id": FAMILY_ID
    }
    try:
        response = requests.post(f"{BASE_URL}/chat/extract", json=extract_data, timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return
        
        result = response.json()
        print(f"Success: {result['success']}")
        parsed_data = result['data']['parsed_data']
        print(f"Extracted Entities: {[e['name'] for e in parsed_data['entities']]}")
        
        # 准备 commit 数据
        print("\n=== 2. 测试数据入库 (Chat Commit) ===")
        # 模拟前端 confirmed 数据格式
        confirmed_entities = []
        for ent in parsed_data['entities']:
            confirmed_entities.append({
                "temp_id": ent['temp_id'],
                "name": ent['name'],
                "gender": ent['gender'],
                "action": "CREATE",
                "tags": ent.get('tags', []),
                "attributes": ent.get('attributes', {})
            })
            
        confirmed_relationships = []
        for rel in parsed_data['relationships']:
            confirmed_relationships.append({
                "source_ref": rel['source_ref'],
                "target_ref": rel['target_ref'],
                "kinship_type": rel['kinship_type'],
                "natural_language_desc": rel['natural_language_desc'],
                "attributes": rel.get('attributes', {})
            })
            
        commit_payload = {
            "family_id": FAMILY_ID,
            "confirmed_entities": confirmed_entities,
            "confirmed_relationships": confirmed_relationships,
            "confirmed_events": [],
            "resolutions": {}
        }
        
        commit_resp = requests.post(f"{BASE_URL}/chat/commit", json=commit_payload, timeout=10)
        print(f"Commit Status: {commit_resp.status_code}")
        commit_result = commit_resp.json()
        print(f"Commit Success: {commit_result['success']}")
        print(f"Actions Taken: {commit_result['data']['actions']}")
        
        print("\n=== 3. 验证数据持久化 ===")
        people_resp = requests.get(f"{BASE_URL}/families/{FAMILY_ID}/people")
        people_data = people_resp.json()
        print(f"People in DB: {[p['name'] for p in people_data['data']]}")
        
    except Exception as e:
        print(f"Smoke test crashed: {str(e)}")

if __name__ == "__main__":
    test_smoke()
