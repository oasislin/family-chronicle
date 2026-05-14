import json
import asyncio
import httpx
from pathlib import Path
import sys

API_BASE = "http://localhost:8000"
TEST_FILE = "复杂测试样例：林家 × 王家（26条自然语言输入）"

def log(msg):
    print(msg, flush=True)
    with open("test_execution.log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

async def run_test():
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. 创建新家族
        log("🚀 [Step 1] Creating new family...")
        try:
            resp = await client.post(f"{API_BASE}/api/families?name=LinWang_Regression")
            resp.raise_for_status()
            family_id = resp.json()["data"]["family_id"]
            log(f"✅ Created family_id: {family_id}\n")
        except Exception as e:
            log(f"❌ Failed to create family: {e}")
            return

        # 2. 读取测试用例
        test_path = Path(__file__).parent.parent / TEST_FILE
        if not test_path.exists():
            log(f"❌ Test file not found: {test_path}")
            return
            
        with open(test_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        log(f"📖 [Step 2] Loaded {len(lines)} test cases.\n")

        # 3. 逐条执行提取和入库
        execution_results = []
        for i, text in enumerate(lines):
            log(f"[{i+1}/{len(lines)}] 📝 Input: {text}")
            
            try:
                # 第一步：提取
                extract_resp = await client.post(f"{API_BASE}/api/chat/extract", json={
                    "text": text,
                    "family_id": family_id
                })
                extract_resp.raise_for_status()
                extract_data = extract_resp.json()["data"]
                parsed_data = extract_data["parsed_data"]
                tasks = parsed_data.get("tasks", [])
                
                if tasks:
                    log(f"  ⚠️  Found {len(tasks)} interaction tasks.")
                    for t in tasks:
                        log(f"    - {t['category']}: {t['message']}")

                # 第二步：准备提交载荷
                commit_payload = {
                    "family_id": family_id,
                    "confirmed_entities": [
                        {
                            "temp_id": e["temp_id"],
                            "name": e["name"],
                            "gender": e["gender"],
                            "action": "CREATE" if e.get("is_new", True) else "LINK_EXISTING",
                            "matched_db_id": e.get("matched_db_id")
                        } for e in parsed_data.get("entities", [])
                    ],
                    "confirmed_relationships": parsed_data.get("relationships", []),
                    "confirmed_events": parsed_data.get("events", []),
                    "resolutions": {} 
                }

                # 第三步：提交入库
                commit_resp = await client.post(f"{API_BASE}/api/chat/commit", json=commit_payload)
                commit_resp.raise_for_status()
                commit_result = commit_resp.json()
                
                if commit_result["success"]:
                    log(f"  ✅ Committed: {commit_result['message']}")
                else:
                    log(f"  ❌ Commit failed: {commit_result['message']}")

                execution_results.append({
                    "index": i + 1,
                    "input": text,
                    "tasks": tasks,
                    "commit_success": commit_result["success"]
                })
            except Exception as e:
                log(f"  ❌ Error processing line {i+1}: {e}")
                
            log("-" * 40)

        # 4. 导出最终图谱并验证逻辑
        log("\n📊 [Step 3] Exporting final graph and verifying logic...")
        try:
            export_resp = await client.get(f"{API_BASE}/api/families/{family_id}/export")
            export_resp.raise_for_status()
            graph = export_resp.json()["data"]
            
            people = graph.get("people", [])
            relationships = graph.get("relationships", [])
            ambiguities = graph.get("ambiguities", [])
            
            log(f"📈 Result: {len(people)} people, {len(relationships)} relationships, {len(ambiguities)} ambiguities remaining.")

            # 保存结果用于报告
            report_data = {
                "family_id": family_id,
                "execution_log": execution_results,
                "final_stats": {
                    "people_count": len(people),
                    "rel_count": len(relationships),
                    "ambiguity_count": len(ambiguities)
                }
            }
            
            with open("regression_test_result.json", "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            log("\n✨ Regression test finished. Results saved to regression_test_result.json")
        except Exception as e:
            log(f"❌ Export failed: {e}")

if __name__ == "__main__":
    # 清理日志
    if Path("test_execution.log").exists():
        Path("test_execution.log").unlink()
    asyncio.run(run_test())
