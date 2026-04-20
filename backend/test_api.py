"""
家族编年史智能族谱系统 - 后端测试脚本
Family Chronicle Intelligent Genealogy System - Backend Test Script

用于验证后端API的基本功能。
"""

import requests
import json
import time
import sys
from pathlib import Path

# API基础URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """测试健康检查接口"""
    print("=== 测试健康检查接口 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_create_family():
    """测试创建家族"""
    print("\n=== 测试创建家族 ===")
    try:
        response = requests.post(
            f"{BASE_URL}/api/families",
            params={"name": "测试家族"}
        )
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        if data.get("success"):
            return data["data"]["family_id"]
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_create_person(family_id):
    """测试创建人物"""
    print(f"\n=== 测试创建人物 (家族ID: {family_id}) ===")
    try:
        person_data = {
            "name": "王建国",
            "gender": "male",
            "birth_date": "1980-12-08",
            "tags": ["老二", "手艺人"],
            "current_residence": "县城"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/families/{family_id}/people",
            json=person_data
        )
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        if data.get("success"):
            return data["data"]["person_id"]
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_create_event(family_id):
    """测试创建事件"""
    print(f"\n=== 测试创建事件 (家族ID: {family_id}) ===")
    try:
        event_data = {
            "type": "marriage",
            "description": "王建国与李梅结婚",
            "date": "1995-09-15",
            "date_accuracy": "exact",
            "location": "县城",
            "participants": [
                {"person_id": "temp_person_001", "role": "新郎"},
                {"person_id": "temp_person_002", "role": "新娘"}
            ],
            "source": "测试数据",
            "confidence": "high"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/families/{family_id}/events",
            json=event_data
        )
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        if data.get("success"):
            return data["data"]["event_id"]
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_ai_parse():
    """测试AI解析接口"""
    print("\n=== 测试AI解析接口 ===")
    try:
        parse_data = {
            "text": "大伯的老二建国，95年和李梅二婚了，后来认了村长赵大爷做干爹",
            "options": {"language": "zh"}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ai/parse",
            json=parse_data
        )
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return data.get("success", False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_conflict_check(family_id):
    """测试冲突检测接口"""
    print(f"\n=== 测试冲突检测 (家族ID: {family_id}) ===")
    try:
        conflict_data = {
            "family_id": family_id,
            "new_data": {
                "entities": [
                    {
                        "type": "person",
                        "name": "王建国",
                        "temp_id": "temp_person_001"
                    }
                ]
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/conflict/check",
            json=conflict_data
        )
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return data.get("success", False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_list_people(family_id):
    """测试获取人物列表"""
    print(f"\n=== 测试获取人物列表 (家族ID: {family_id}) ===")
    try:
        response = requests.get(
            f"{BASE_URL}/api/families/{family_id}/people"
        )
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return data.get("success", False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_export_data(family_id):
    """测试导出数据"""
    print(f"\n=== 测试导出数据 (家族ID: {family_id}) ===")
    try:
        response = requests.get(
            f"{BASE_URL}/api/families/{family_id}/export"
        )
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return data.get("success", False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("开始运行家族编年史API测试...")
    print("=" * 50)
    
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(2)
    
    # 测试健康检查
    if not test_health_check():
        print("服务器未启动，请先启动API服务器：")
        print("cd family-chronicle/backend && python main.py")
        return False
    
    # 创建测试家族
    family_id = test_create_family()
    if not family_id:
        print("创建家族失败")
        return False
    
    # 测试创建人物
    person_id = test_create_person(family_id)
    
    # 测试创建事件
    event_id = test_create_event(family_id)
    
    # 测试AI解析
    test_ai_parse()
    
    # 测试冲突检测
    test_conflict_check(family_id)
    
    # 测试获取人物列表
    test_list_people(family_id)
    
    # 测试导出数据
    test_export_data(family_id)
    
    print("\n" + "=" * 50)
    print("所有测试完成！")
    return True

if __name__ == "__main__":
    # 检查是否安装了requests
    try:
        import requests
    except ImportError:
        print("请先安装requests库：pip install requests")
        sys.exit(1)
    
    # 运行测试
    success = run_all_tests()
    sys.exit(0 if success else 1)