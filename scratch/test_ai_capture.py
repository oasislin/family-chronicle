import requests
import json
import os

def test_capture():
    url = "http://localhost:8000/api/chat/extract"
    payload = {
        "family_id": "test_debug",
        "text": "林大明和妻子赵春花"
    }
    print(f"发送测试请求到 {url}...")
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"服务器响应状态码: {response.status_code}")
        
        # 检查文件是否生成
        target_file = r"c:\SynologyDrive\Project\family-chronicle\data\A_test_data.json"
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                print("SUCCESS: 抓取到 AI 原始数据 A!")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:200] + "...")
        else:
            print(f"FAILURE: 文件 {target_file} 仍未生成。")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    test_capture()
