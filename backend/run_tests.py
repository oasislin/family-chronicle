"""
家族编年史 - 测试执行器
逐条执行测试用例，对比实际结果与预期，生成报告。
"""

import json
import sys
import time
import httpx
import copy
from datetime import datetime

API_BASE = "http://localhost:8000"

def load_test_cases():
    with open("test_cases.json", "r", encoding="utf-8") as f:
        return json.load(f)

def reset_family_data():
    """重置为基准数据"""
    base = load_test_cases()
    graph_data = {
        "people": base["base_people"],
        "events": [],
        "relationships": base["base_relationships"],
    }
    # 获取或创建 family
    resp = httpx.get(f"{API_BASE}/api/families")
    families = resp.json().get("data", [])

    if families:
        family_id = families[0]["family_id"]
    else:
        resp = httpx.post(f"{API_BASE}/api/families?name=测试家族")
        family_id = resp.json()["data"]["family_id"]

    # 导入基准数据
    httpx.post(f"{API_BASE}/api/families/{family_id}/import", json=graph_data)
    return family_id

def run_ai_parse(text: str) -> dict:
    """调用 AI 解析"""
    resp = httpx.post(
        f"{API_BASE}/api/ai/parse",
        json={"text": text},
        timeout=120.0,
    )
    data = resp.json()
    if data.get("success") and data.get("data"):
        return data["data"].get("parsed_data", {})
    return {}

def run_auto_import(family_id: str, parsed_data: dict, answers: dict = None):
    """调用自动导入"""
    resp = httpx.post(
        f"{API_BASE}/api/families/{family_id}/auto-import",
        json={"parsed_data": parsed_data, "answers": answers or {}},
        timeout=60.0,
    )
    return resp.json()

def get_family_state(family_id: str):
    """获取当前家族状态"""
    resp = httpx.get(f"{API_BASE}/api/families/{family_id}/export")
    return resp.json().get("data", {})

def evaluate_result(test_case: dict, parsed_data: dict, import_result: dict, before: dict, after: dict):
    """评估单条测试结果"""
    actual_actions = import_result.get("data", {}).get("actions", [])
    questions = import_result.get("data", {}).get("questions", [])
    auto_saved = import_result.get("data", {}).get("auto_saved", False)

    result = {
        "id": test_case["id"],
        "input": test_case["input"][:60],
        "category": test_case["category"],
        "expected": [],
        "actual": [],
        "verdict": "PASS",  # PASS / FAIL / PARTIAL / SKIP
        "details": "",
    }

    # 检查 AI 解析
    entities_count = len(parsed_data.get("entities", []))
    events_count = len(parsed_data.get("events", []))
    rels_count = len(relationships := parsed_data.get("relationships", []))

    # 检查实际新增
    people_before = {p["name"] for p in before.get("people", [])}
    people_after = {p["name"] for p in after.get("people", [])}
    new_people = people_after - people_before

    rels_before_count = len(before.get("relationships", []))
    rels_after_count = len(after.get("relationships", []))
    new_rels_count = rels_after_count - rels_before_count

    events_before_count = len(before.get("events", []))
    events_after_count = len(after.get("events", []))
    new_events_count = events_after_count - events_before_count

    # 匹配预期
    expected = test_case.get("expected_actions", [])
    exp_actions = [e["action"] for e in expected]

    # NO_ACTION
    if "NO_ACTION" in exp_actions:
        if entities_count == 0 and events_count == 0 and len(rels_count) == 0:
            result["verdict"] = "PASS"
            result["details"] = "正确识别为无有效信息"
        elif not auto_saved and entities_count > 0:
            result["verdict"] = "PARTIAL"
            result["details"] = f"AI提取了{entities_count}个实体但未自动保存"
        else:
            result["verdict"] = "FAIL"
            result["details"] = f"预期无操作，但AI提取了{entities_count}个人/{events_count}个事件"

    # CREATE_PERSON
    elif "CREATE_PERSON" in exp_actions:
        if len(new_people) > 0:
            result["verdict"] = "PASS"
            result["details"] = f"新增人物: {', '.join(new_people)}"
        elif auto_saved:
            result["verdict"] = "PARTIAL"
            result["details"] = f"自动保存但无新人物（可能匹配到已有人员）"
        else:
            result["verdict"] = "FAIL"
            result["details"] = f"预期新增人物，但未创建。AI识别了{entities_count}个实体"

    # MATCH_PERSON
    elif "MATCH_PERSON" in exp_actions:
        if auto_saved and entities_count > 0:
            result["verdict"] = "PASS"
            result["details"] = f"成功关联已有人员，操作: {', '.join(actual_actions[:3])}"
        elif len(questions) > 0:
            result["verdict"] = "PARTIAL"
            result["details"] = f"需要用户确认: {questions[0].get('message', '')}"
        else:
            result["verdict"] = "FAIL"
            result["details"] = "预期关联已有人员但未实现"

    # UPDATE_PERSON
    elif "UPDATE_PERSON" in exp_actions:
        if any("更新" in a for a in actual_actions):
            result["verdict"] = "PASS"
            result["details"] = f"更新成功: {', '.join([a for a in actual_actions if '更新' in a])}"
        elif auto_saved:
            result["verdict"] = "PARTIAL"
            result["details"] = f"已保存但未检测到更新操作: {', '.join(actual_actions)}"
        else:
            result["verdict"] = "FAIL"
            result["details"] = "预期更新人物但未实现"

    # CREATE_RELATIONSHIP
    elif "CREATE_RELATIONSHIP" in exp_actions:
        if new_rels_count > 0:
            result["verdict"] = "PASS"
            result["details"] = f"新增{new_rels_count}条关系"
        elif auto_saved:
            result["verdict"] = "PARTIAL"
            result["details"] = f"已保存但无新关系（可能重复）"
        else:
            result["verdict"] = "FAIL"
            result["details"] = f"预期新增关系，AI识别了{rels_count}条"

    # SKIP_RELATIONSHIP
    elif "SKIP_RELATIONSHIP" in exp_actions:
        if new_rels_count == 0:
            result["verdict"] = "PASS"
            result["details"] = "正确跳过重复关系"
        else:
            result["verdict"] = "FAIL"
            result["details"] = f"预期跳过重复，但新增了{new_rels_count}条关系"

    # CREATE_EVENT
    elif "CREATE_EVENT" in exp_actions:
        if new_events_count > 0:
            result["verdict"] = "PASS"
            result["details"] = f"新增{new_events_count}个事件"
        else:
            result["verdict"] = "FAIL"
            result["details"] = f"预期新增事件，AI识别了{events_count}个"

    # UPDATE_STORY
    elif "UPDATE_STORY" in exp_actions:
        if auto_saved:
            result["verdict"] = "PASS"
            result["details"] = f"操作: {', '.join(actual_actions[:3])}"
        else:
            result["verdict"] = "PARTIAL"
            result["details"] = "AI可能将信息识别为story但未直接体现"

    # ASK_QUESTION
    elif "ASK_QUESTION" in exp_actions:
        if len(questions) > 0:
            result["verdict"] = "PASS"
            result["details"] = f"正确触发提问: {questions[0].get('message', '')}"
        else:
            result["verdict"] = "FAIL"
            result["details"] = "预期需要确认但直接处理了"

    else:
        result["verdict"] = "SKIP"
        result["details"] = "无法自动评估"

    result["expected"] = exp_actions
    result["actual"] = actual_actions[:5]
    result["ai_entities"] = entities_count
    result["ai_events"] = events_count
    result["ai_relationships"] = rels_count

    return result


def main():
    print("=" * 60)
    print("家族编年史 — 测试执行器")
    print("=" * 60)

    data = load_test_cases()
    test_cases = data["test_cases"]
    total = len(test_cases)

    print(f"\n共 {total} 条测试用例")
    print(f"分类: {json.dumps(data['categories'], ensure_ascii=False)}")

    # 确认后端可用
    try:
        httpx.get(f"{API_BASE}/api/health", timeout=5.0)
    except Exception:
        print("\n❌ 后端未启动！请先运行: cd backend && python main.py")
        sys.exit(1)

    # 重置数据
    print("\n📌 重置基准数据...")
    family_id = reset_family_data()
    print(f"   Family ID: {family_id}")

    # 执行测试
    results = []
    stats = {"PASS": 0, "FAIL": 0, "PARTIAL": 0, "SKIP": 0}

    print(f"\n🚀 开始执行 {total} 条测试...\n")

    for i, tc in enumerate(test_cases):
        tc_id = tc["id"]
        input_text = tc["input"]

        if not input_text.strip():
            stats["SKIP"] += 1
            results.append({
                "id": tc_id, "input": "(空)", "category": tc["category"],
                "verdict": "SKIP", "details": "空输入", "expected": [], "actual": [],
            })
            continue

        # 每10条重置数据（避免干扰）
        if i % 10 == 0:
            family_id = reset_family_data()

        before = get_family_state(family_id)

        try:
            # Step 1: AI 解析
            parsed = run_ai_parse(input_text)

            # Step 2: 自动导入
            import_result = run_auto_import(family_id, parsed)

            after = get_family_state(family_id)

            # Step 3: 评估
            result = evaluate_result(tc, parsed, import_result, before, after)
        except Exception as e:
            result = {
                "id": tc_id,
                "input": input_text[:60],
                "category": tc["category"],
                "verdict": "FAIL",
                "details": f"执行异常: {str(e)}",
                "expected": [],
                "actual": [],
            }

        stats[result["verdict"]] = stats.get(result["verdict"], 0) + 1
        results.append(result)

        # 进度
        icon = {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠️", "SKIP": "⏭️"}.get(result["verdict"], "?")
        if i % 5 == 0 or result["verdict"] in ("FAIL",):
            print(f"  [{i+1}/{total}] {icon} {tc_id} {tc['category']}: {input_text[:40]}...")

    # 输出报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "stats": stats,
        "pass_rate": f"{stats['PASS'] / (total - stats['SKIP']) * 100:.1f}%" if (total - stats['SKIP']) > 0 else "N/A",
        "results": results,
    }

    with open("test_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 打印汇总
    print("\n" + "=" * 60)
    print("测试报告汇总")
    print("=" * 60)
    print(f"  总计: {total} 条")
    print(f"  ✅ PASS: {stats['PASS']}")
    print(f"  ❌ FAIL: {stats['FAIL']}")
    print(f"  ⚠️ PARTIAL: {stats['PARTIAL']}")
    print(f"  ⏭️ SKIP: {stats['SKIP']}")
    print(f"  通过率: {report['pass_rate']}")

    # 列出 FAIL 项
    fails = [r for r in results if r["verdict"] == "FAIL"]
    if fails:
        print(f"\n❌ 失败项 ({len(fails)} 条):")
        for f in fails[:20]:
            print(f"  {f['id']}: [{f['category']}] {f['input']}")
            print(f"    预期: {f.get('expected', [])}")
            print(f"    实际: {f.get('actual', [])}")
            print(f"    原因: {f['details']}")

    print(f"\n📄 完整报告: test_report.json")


if __name__ == "__main__":
    main()
