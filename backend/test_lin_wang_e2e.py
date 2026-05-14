import json
import time
import httpx
import os

API_BASE = "http://localhost:8000"
INPUT_FILE = "../test_input.txt"

def read_inputs():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip()]

def create_family():
    resp = httpx.post(f"{API_BASE}/api/families?name=林王家族_Test")
    resp.raise_for_status()
    return resp.json()["data"]["family_id"]

def parse_text(text: str):
    print(f"  [AI Parsing] ...", end="", flush=True)
    resp = httpx.post(f"{API_BASE}/api/ai/parse", json={"text": text}, timeout=120.0)
    resp.raise_for_status()
    data = resp.json()["data"]["parsed_data"]
    print(f" Done. Found {len(data.get('entities', []))} entities, {len(data.get('relationships', []))} relationships.")
    return data

def auto_import(family_id: str, parsed_data: dict, answers: dict = None):
    payload = {"parsed_data": parsed_data, "answers": answers or {}}
    resp = httpx.post(f"{API_BASE}/api/families/{family_id}/auto-import", json=payload, timeout=60.0)
    if resp.status_code != 200:
        print(f"  [ERROR] {resp.status_code}: {resp.text}")
    resp.raise_for_status()
    return resp.json()["data"]

def get_graph(family_id: str):
    resp = httpx.get(f"{API_BASE}/api/families/{family_id}/export")
    resp.raise_for_status()
    return resp.json()["data"]

def main():
    # 确保后端已启动
    try:
        httpx.get(f"{API_BASE}/api/health", timeout=5.0)
    except httpx.RequestError:
        print("❌ 无法连接到后端服务器，请确保 'python main.py' 正在运行。")
        return

    print("=" * 60)
    print("林家 × 王家 E2E 复杂用例测试开始")
    print("=" * 60)

    lines = read_inputs()
    print(f"共加载 {len(lines)} 条输入。\n")

    family_id = create_family()
    print(f"已创建测试家族 ID: {family_id}\n")

    execution_log = []

    for i, line in enumerate(lines):
        print(f"[{i+1}/{len(lines)}] 输入: {line}")
        try:
            parsed = parse_text(line)
            
            # 首次导入尝试
            import_result = auto_import(family_id, parsed)
            questions = import_result.get("questions", [])
            actions = import_result.get("actions", [])
            
            # 如果需要二次确认
            if questions and not import_result.get("auto_saved"):
                print(f"  [Auto Import] Requires user confirmation for {len(questions)} questions.")
                answers = {}
                for q in questions:
                    q_id = q["id"]
                    q_type = q.get("type")
                    
                    if q_type == "ambiguous_person" or q_type == "person_match":
                        # 默认策略：如果有同名候选人，直接合并到第一个
                        candidates = q.get("candidates", [])
                        if candidates:
                            answers[q_id] = candidates[0]["id"]
                            print(f"    -> Auto-answered '{q_id}': merge to {candidates[0]['name']}")
                        else:
                            answers[q_id] = "__new__"
                            print(f"    -> Auto-answered '{q_id}': create new")
                    elif q_type == "entity_confirm":
                        answers[q_id] = "__create__:" + q.get("original_name", "")
                        print(f"    -> Auto-answered '{q_id}': entity_confirm -> create new")
                    elif q_type == "person_name":
                        answers[q_id] = "__new__"
                        print(f"    -> Auto-answered '{q_id}': person_name -> create new")
                    else:
                        # 其他类型的问题
                        answers[q_id] = "__new__"
                        print(f"    -> Auto-answered '{q_id}': {q_type} -> create new (fallback)")

                # 带上 answers 再次导入
                print("  [Auto Import] Retrying with answers...")
                import_result = auto_import(family_id, parsed, answers)
                actions = import_result.get("actions", [])

            # 打印最终执行结果
            saved = import_result.get("auto_saved", False)
            if saved:
                print(f"  [Result] 自动保存成功! 执行了 {len(actions)} 个动作:")
                for a in actions[:3]:
                    print(f"    - {a}")
                if len(actions) > 3:
                    print(f"    - ... (共 {len(actions)} 个)")
            else:
                print("  [Result] ⚠️ 保存失败或仍有未解决的问题。")

            execution_log.append({
                "step": i + 1,
                "input": line,
                "parsed": parsed,
                "import_result": import_result
            })
            print("-" * 60)

        except Exception as e:
            print(f"  [ERROR] 处理失败: {e}")
            execution_log.append({
                "step": i + 1,
                "input": line,
                "error": str(e)
            })
            print("-" * 60)

    # 保存日志和最终家谱
    with open("lin_wang_execution_log.json", "w", encoding="utf-8") as f:
        json.dump(execution_log, f, ensure_ascii=False, indent=2)
    print("已生成详细日志：lin_wang_execution_log.json")

    final_graph = get_graph(family_id)
    with open("lin_wang_final_graph.json", "w", encoding="utf-8") as f:
        json.dump(final_graph, f, ensure_ascii=False, indent=2)
    print("已生成最终图谱数据：lin_wang_final_graph.json")

    people = final_graph.get("people", [])
    rels = final_graph.get("relationships", [])
    print("\n最终图谱统计:")
    print(f"  人物数量: {len(people)}")
    print(f"  关系数量: {len(rels)}")

if __name__ == "__main__":
    main()
