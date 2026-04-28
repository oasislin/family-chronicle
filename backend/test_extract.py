import requests
import json

def test_extract():
    url = "http://localhost:8000/api/chat/extract"
    payload = {
        "text": "王大壮是王小明的父亲，王小明出生于1990年，现在住在西安。",
        "family_id": "family_20260418_175214" # 使用现有的一个家族ID
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if result["success"]:
            print("Successfully extracted data from LLM:")
            print(json.dumps(result["data"], indent=2, ensure_ascii=False))
        else:
            print(f"Extraction failed: {result['message']}")
            
    except Exception as e:
        print(f"Error during request: {e}")

if __name__ == "__main__":
    # 确保后端已经启动在 8000 端口
    test_extract()
