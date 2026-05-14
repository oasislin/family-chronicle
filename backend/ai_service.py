import json
import re
import uuid
import httpx
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger

from models import Gender, RelationshipType, InteractionTask, InteractionTaskCategory, InteractionTaskType
from fact_store import load_facts, append_facts, FactLog
from compiler_engine import CompilerEngine
from prompt_engineering import InteractiveExtractionPrompt, KinshipDecompositionPrompt
from config import get_ai_provider_config
from history import record_action, get_recent_history
from fact_service import load_family_graph, get_relationship_summary

# 初始化提示词管理器
interactive_prompt_manager = InteractiveExtractionPrompt()

def _log_pipeline_event(family_id: str, event_type: str, data: Any):
    """统一审计日志记录"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "pipeline.log"
    
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "family_id": family_id,
        "event_type": event_type,
        "data": data
    }
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Audit log failed: {str(e)}")

_log_pipeline_event("SYSTEM", "INIT", {"msg": "ai_service loaded"})

async def perform_ai_extraction(text: str, family_id: str):
    """
    交互式提取核心逻辑 (Refactored Phase 3.1):
    解耦 AI 提取与后处理审计逻辑。
    """
    _log_pipeline_event(family_id, "EXTRACT_START", {"input_text": text})
    
    # 1. 收集上下文
    context_people = _get_extraction_context(family_id, text)
    
    # 2. 调用 LLM 获取原始提取数据
    raw_parsed_data, prompt_used = await _call_llm_for_extraction(text, context_people, family_id)
    
    # 3. 确定性匹配与对齐 (Reconciliation)
    reconciled_data = _reconcile_entities(family_id, raw_parsed_data)
    _log_pipeline_event(family_id, "EXTRACT_RECONCILED", reconciled_data)
    
    # 4. 图谱逻辑审计 (Auditing)
    audit_results = _audit_graph_logic(family_id, reconciled_data)
    _log_pipeline_event(family_id, "EXTRACT_AUDITED", audit_results)
    
    return {
        "parsed_data": {
            **reconciled_data,
            **audit_results
        },
        "prompt_used": prompt_used
    }

def _get_extraction_context(family_id: str, text: str) -> List[Dict[str, Any]]:
    """收集用于 AI 解析的上下文人物信息"""
    graph = load_family_graph(family_id)
    mentioned_people = find_mentioned_people(graph, text)
    mentioned_ids = {p["id"] for p in mentioned_people}
    context_people = mentioned_people
    
    if len(context_people) < 8:
        recent_history = get_recent_history(family_id, limit=20)
        recent_pids = []
        for h in reversed(recent_history):
            pid = h.get("target_id")
            if h.get("target_type") == "person" and pid and pid not in mentioned_ids and pid not in recent_pids:
                recent_pids.append(pid)
            if len(recent_pids) + len(context_people) >= 8: break
        
        for pid in recent_pids:
            p = graph.get_person(pid)
            if p:
                context_people.append({
                    "id": p.id,
                    "name": p.name,
                    "gender": "M" if p.gender == Gender.MALE else "F" if p.gender == Gender.FEMALE else "UNKNOWN",
                    "relationship_summary": get_relationship_summary(graph, p.id)
                })
    return context_people

async def _call_llm_for_extraction(text: str, context_people: List[Dict[str, Any]], family_id: str):
    """纯粹的 AI 调用逻辑，仅负责提取文本中的结构化信息"""
    messages = interactive_prompt_manager.get_prompt(text, context_people)
    
    _log_pipeline_event(family_id, "AI_PROMPT", {"messages": messages})
    provider_config = get_ai_provider_config()
    
    if not provider_config.get("api_key"):
        raise Exception("未配置 AI API 密钥")

    url = f"{provider_config['base_url']}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {provider_config['api_key']}"
    }
    payload = {
        "model": provider_config["model"],
        "messages": messages,
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # 审计日志：保存 AI 原始返回
        _log_pipeline_event(family_id, "AI_RAW_RESPONSE", {"content": content})
        
        # 解析 JSON
        try:
            parsed_data = json.loads(content)
        except:
            match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if match:
                parsed_data = json.loads(match.group(1))
            else:
                raise Exception("无法解析 LLM 返回的 JSON")

        return parsed_data, {
            "system": messages[0]["content"],
            "user": messages[1]["content"]
        }

def _reconcile_entities(family_id: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    实体对齐逻辑：将 AI 提取的实体与数据库中的人物进行确定性匹配。
    这部分逻辑完全由程序控制，不依赖 AI。
    """
    graph = load_family_graph(family_id)
    existing_names = {p.name: p.id for p in graph.people.values()}
    
    new_entities = []
    for ent in parsed_data.get("entities", []):
        name = ent.get("name")
        reconciled_ent = ent.copy()
        
        # 如果名字匹配到已有成员，则强制关联
        if name in existing_names:
            reconciled_ent["matched_db_id"] = existing_names[name]
            reconciled_ent["is_new"] = False
            reconciled_ent["reason"] = f"程序自动匹配到已有成员：{name}"
        
        new_entities.append(reconciled_ent)
    
    parsed_data["entities"] = new_entities
    return parsed_data

def _auto_answer_clarification_questions(compiler: CompilerEngine, questions: List[Dict], parsed_data: Dict[str, Any]) -> List[Dict]:
    """
    自动回答 AI 提出的澄清问题

    对于可以通过现有图谱数据直接推导的问题，自动回答并从列表中移除。
    使用结构化的澄清问题数据，无需正则表达式解析。
    """
    from compiler_engine import KINSHIP_DICT

    filtered_questions = []

    # 调试日志：检查 AI 返回的数据格式
    if questions:
        logger.info(f"澄清问题数量: {len(questions)}")
        logger.info(f"第一个问题类型: {type(questions[0])}")
        if isinstance(questions[0], dict):
            logger.info(f"第一个问题结构: {json.dumps(questions[0], ensure_ascii=False)}")
        else:
            logger.info(f"第一个问题内容: {questions[0]}")

    # 构建名称到ID的映射
    name_to_id = {p.name: p.id for p in compiler.graph.people.values()}
    entities = {e["name"]: e["temp_id"] for e in parsed_data.get("entities", [])}
    name_to_id.update(entities)

    # 构建临时ID到真实ID的映射
    temp_to_real_id = {}
    for ent in parsed_data.get("entities", []):
        if "temp_id" in ent:
            if "matched_db_id" in ent and ent["matched_db_id"]:
                temp_to_real_id[ent["temp_id"]] = ent["matched_db_id"]
            else:
                temp_to_real_id[ent["temp_id"]] = ent["temp_id"]

    for q in questions:
        # 检查是否是结构化问题
        if isinstance(q, dict) and "relationship_type" in q:
            person1_temp_id = q.get("person1_temp_id")
            person2_temp_id = q.get("person2_temp_id")
            rel_type = q.get("relationship_type")
            question_text = q.get("question", "")
            
            # 获取人物真实ID
            person_a = temp_to_real_id.get(person1_temp_id) or person1_temp_id
            person_b = temp_to_real_id.get(person2_temp_id) or person2_temp_id
            
            if not person_a or not person_b:
                filtered_questions.append(q)
                continue
                
            # 获取关系定义
            rel_def = KINSHIP_DICT.get(rel_type)
            if not rel_def:
                # 未知关系类型，记录日志
                logger.warning(
                    f"[未来模块预留] 遇到未定义关系类型: '{rel_type}' "
                    f"在问题 '{question_text}' 中。系统暂无法自动处理此类关系。"
                )
                filtered_questions.append(q)
                continue
                
            path = rel_def.get("path", [])
            if not path:
                filtered_questions.append(q)
                continue
                
            # 验证关系路径
            if _verify_kinship_path(compiler, person_a, person_b, path):
                logger.info(f"自动回答澄清问题: '{question_text}' -> 已确认存在 {rel_type} 关系")
                # 跳过此问题（不添加到 filtered_questions）
                continue
            else:
                filtered_questions.append(q)
        else:
            # 非结构化问题格式，保留待用户确认
            logger.warning(f"收到非结构化澄清问题格式，保留待用户确认: {q}")
            filtered_questions.append(q)

    return filtered_questions


def _verify_kinship_path(compiler: CompilerEngine, person_a: str, person_b: str, path: List[Dict[str, Any]]) -> bool:
    """
    验证 person_a 和 person_b 之间是否存在指定的亲属关系路径

    参数：
        compiler: 编译引擎
        person_a: 关系主体（如外婆）
        person_b: 关系客体（如外孙）
        path: KINSHIP_DICT 中定义的关系路径

    返回：
        是否存在该关系
    """
    current_id = person_b
    
    for step in path:
        direction = step.get("direction")
        step_type = step.get("type", "parent_child")
        expected_gender = step.get("gender")
        biological_only = step.get("biological_only", False)
        
        candidates = compiler._find_candidate_nodes(current_id, direction, expected_gender, biological_only=biological_only)
        
        if not candidates:
            return False
        
        found = False
        for cand_id in candidates:
            if step_type == "parent_child":
                if compiler._edge_exists(cand_id, current_id, "parent_child"):
                    current_id = cand_id
                    found = True
                    break
            elif step_type == "spouse":
                if compiler._edge_exists(current_id, cand_id, "spouse") or compiler._edge_exists(cand_id, current_id, "spouse"):
                    current_id = cand_id
                    found = True
                    break
        
        if not found:
            return False
    
    return current_id == person_a

def _audit_graph_logic(family_id: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    图谱逻辑审计：模拟入库并利用推导引擎检测歧义和冲突。
    """
    potential_merges = []
    
    try:
        compiler = CompilerEngine(family_id)
        # 加载当前事实进行模拟
        compiler.compile(load_facts(family_id))
        
        # 1. 查找潜在合并（即使没有自动关联，也作为建议提供）
        existing_names = {p.name: p.id for p in compiler.graph.people.values()}
        for ent in parsed_data.get("entities", []):
            name = ent.get("name")
            if name in existing_names and ent.get("is_new") is not False:
                db_id = existing_names[name]
                potential_merges.append({
                    "temp_id": ent["temp_id"],
                    "matched_db_id": db_id,
                    "name": name,
                    "message": f"库中已存在名为 '{name}' 的成员，建议合并。"
                })
        
        # 2. 语义一致性审计 (Semantic Consistency Guard)
        # 在模拟运行前，先检查明显的性别/方向矛盾
        semantic_conflicts = _check_semantic_consistency(compiler, parsed_data)
        
        # 3. 复用“执行逻辑”进行模拟 (Dry Run)
        # 将解析出的实体和关系转化为 Fact 并应用到编译器图中
        _apply_extraction_to_compiler(
            compiler, 
            parsed_data.get("entities", []), 
            parsed_data.get("relationships", []),
            parsed_data.get("events", []),
            record=False # 仅模拟，不记录
        )
        
        # [CRITICAL FIX] 必须重新运行推导，以捕获由于新加入的边触发的新歧义
        compiler._run_inference_pass()
        
        ambiguities = compiler.ambiguities + semantic_conflicts
        
        # [NEW] 自动回答可推导的澄清问题
        original_questions = parsed_data.get("clarification_questions", [])
        # 调试日志：查看 AI 返回的数据格式
        if original_questions:
            logger.info(f"澄清问题数据格式: {type(original_questions[0])}")
            if isinstance(original_questions[0], dict):
                logger.info(f"第一个问题结构: {json.dumps(original_questions[0], ensure_ascii=False)}")
            else:
                logger.info(f"第一个问题内容: {original_questions[0]}")
        filtered_questions = _auto_answer_clarification_questions(compiler, original_questions, parsed_data)
        logger.info(f"自动回答澄清问题: 原始 {len(original_questions)} 个，过滤后 {len(filtered_questions)} 个")
        
    except Exception as e:
        logger.warning(f"Graph logic audit failed: {e}")
        ambiguities = []
        filtered_questions = parsed_data.get("clarification_questions", [])

    return {
        "tasks": _unify_to_interaction_tasks(ambiguities, potential_merges, filtered_questions),
        "ambiguous_derivations": ambiguities, 
        "potential_merges": potential_merges
    }

def _check_semantic_consistency(compiler: CompilerEngine, parsed_data: Dict[str, Any]) -> List[Dict]:
    """检查提取结果中的性别与称谓冲突、方向性矛盾"""
    conflicts = []
    entities = {e["temp_id"]: e for e in parsed_data.get("entities", [])}
    
    # 建立临时 ID 到性别的映射
    def get_gender(ref_id):
        # 先看提取的数据
        if ref_id in entities:
            g = entities[ref_id].get("gender")
            if g == "M": return Gender.MALE
            if g == "F": return Gender.FEMALE
        # 再看库里已有的
        p = compiler.graph.get_person(ref_id)
        if p: return p.gender
        return Gender.UNKNOWN

    for i, rel in enumerate(parsed_data.get("relationships", [])):
        src_id = rel["source_ref"]
        tgt_id = rel["target_ref"]
        k_type = rel.get("kinship_type")
        src_gender = get_gender(src_id)

        # 1. 性别与称谓冲突校验
        # 语义规则: source_ref 是主体，"A 是 B 的 XX"
        # - wife: A 是 B 的妻子 → source 必须是女性
        # - husband: A 是 B 的丈夫 → source 必须是男性
        is_conflict = False
        reason = ""

        if k_type in ["father", "grandfather_paternal", "grandfather_maternal", "uncle_paternal", "uncle_maternal"]:
            if src_gender == Gender.FEMALE:
                is_conflict = True
                reason = f"性别矛盾：提取为'{k_type}'的主语已知为女性。"
        elif k_type in ["mother", "grandmother_paternal", "grandmother_maternal", "aunt_paternal", "aunt_maternal"]:
            if src_gender == Gender.MALE:
                is_conflict = True
                reason = f"性别矛盾：提取为'{k_type}'的主语已知为男性。"
        elif k_type == "wife":
            if src_gender != Gender.FEMALE:
                is_conflict = True
                reason = f"性别矛盾：提取为'wife'的主语已知为男性或性别未知。"
        elif k_type == "husband":
            if src_gender != Gender.MALE:
                is_conflict = True
                reason = f"性别矛盾：提取为'husband'的主语已知为女性或性别未知。"
        
        if is_conflict:
            conflicts.append({
                "type": "LOGIC_CONFLICT",
                "key": f"rel_conflict_{i}",
                "message": f"逻辑冲突：{rel['natural_language_desc']}。{reason}",
                "nodes": [src_id, tgt_id],
                "questionType": "CHOICE",
                "actions": [
                    {
                        "label": f"反转方向 (设为 {entities.get(tgt_id, {'name': '宾语'})['name']} 是 {entities.get(src_id, {'name': '主语'})['name']} 的 {k_type})", 
                        "action": "SWAP_DIRECTION", 
                        "payload": {"rel_idx": i}
                    },
                    {"label": "修正主语性别", "action": "MODIFY_GENDER", "payload": {"temp_id": src_id, "gender": "M" if src_gender == Gender.FEMALE else "F"}},
                    {"label": "忽略此关系", "action": "REJECT_EDGE", "payload": {"rel_idx": i}}
                ]
            })
            
    return conflicts

async def perform_ai_validation(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    交互式扩散验证：模拟当前所有确认项，返回更新后的任务列表。
    """
    family_id = request_data.get("family_id")
    resolutions = request_data.get("resolutions", {})
    
    try:
        compiler = CompilerEngine(family_id)
        compiler.compile(load_facts(family_id))
        
        # 应用当前建议的实体/关系
        _apply_extraction_to_compiler(
            compiler, 
            request_data.get("confirmed_entities", []), 
            request_data.get("confirmed_relationships", []),
            request_data.get("confirmed_events", []),
            record=False
        )
        
        # 应用当前的解析方案
        for key, res_val in resolutions.items():
            if res_val.startswith("ACTION:"):
                # 模拟执行动作以触发扩散
                parts = res_val.split(":", 2)
                if len(parts) >= 3:
                    action_type = parts[1]
                    try:
                        payload = json.loads(parts[2])
                        if action_type == "CREATE_PLACEHOLDER":
                            p_id = f"placeholder_{uuid.uuid4().hex[:8]}"
                            compiler.apply_fact(FactLog(family_id, "ADD_NODE", {
                                "id": p_id,
                                "name": payload.get("name", "未知人物"),
                                "gender": payload.get("gender", "unknown"),
                                "is_placeholder": True
                            }), record=False)
                            compiler.resolutions[key] = p_id
                        else:
                            compiler.apply_fact(FactLog(family_id, action_type, payload), record=False)
                    except: pass
            elif res_val != "CREATE_NEW_PLACEHOLDER":
                compiler.resolutions[key] = res_val
        
        # 重新运行推导以触发扩散
        compiler._run_inference_pass()
        
        # 语义守卫检查 (针对当前 confirmed 数据)
        semantic_conflicts = _check_semantic_consistency(compiler, {
            "entities": request_data.get("confirmed_entities", []),
            "relationships": request_data.get("confirmed_relationships", [])
        })
        
        ambiguities = compiler.ambiguities + semantic_conflicts
        
        # 转换回统一任务
        tasks = _unify_to_interaction_tasks(ambiguities, [], [])
        
        return {
            "tasks": tasks,
            "reply_message": "扩散校验已完成，图谱状态已更新。"
        }
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {"tasks": [], "error": str(e)}

def _unify_to_interaction_tasks(ambiguities: List[Dict], merges: List[Dict], questions: List[str]) -> List[Dict]:
    """将分散的歧义、合并建议和问题统一转化为 InteractionTask 协议"""
    tasks = []
    
    # 1. 处理编译器推导歧义
    for i, amb in enumerate(ambiguities):
        task_type_str = amb.get("questionType", "")
        if task_type_str == "YES_NO":
            task_type = InteractionTaskType.YES_NO
        elif task_type_str == "CHOICE" or task_type_str == "MULTI":
            task_type = InteractionTaskType.MULTI_CHOICE if task_type_str == "MULTI" else InteractionTaskType.SINGLE_CHOICE
        else:
            task_type = InteractionTaskType.SINGLE_CHOICE

        task = InteractionTask(
            task_id=amb.get("key", f"amb_{i}"),
            category=InteractionTaskCategory.CONFLICT if amb.get("type") == "LOGIC_CONFLICT" else InteractionTaskCategory.AMBIGUITY,
            message=amb.get("message", "发现逻辑歧义，请确认。"),
            task_type=task_type
        )
        
        # 处理逻辑冲突的附加信息
        if amb.get("type") == "LOGIC_CONFLICT":
            conflicts = amb.get("conflicts", [])
            if conflicts:
                task.message += "\n" + "\n".join([f"- {c}" for c in conflicts])
            # 添加默认确认选项
            if not amb.get("actions"):
                task.add_option("了解并忽略", "IGNORE_CONFLICT", {})
        # 转换 actions
        for action in amb.get("actions", []):
            task.add_option(
                label=action["label"],
                action=action["action"],
                payload=action.get("payload", {}),
                target_id=action.get("target_id")
            )
            
        tasks.append(task.to_dict())

    # 2. 处理潜在合并建议
    for i, m in enumerate(merges):
        task = InteractionTask(
            task_id=f"merge_{i}",
            category=InteractionTaskCategory.SUGGESTION,
            message=m["message"],
            task_type=InteractionTaskType.YES_NO
        )
        task.add_option(f"合并到 {m['name']}", "LINK_EXISTING", {"matched_db_id": m["matched_db_id"], "temp_id": m["temp_id"]})
        task.add_option("作为新人物保留", "IGNORE", {})
        tasks.append(task.to_dict())

    # 3. 处理 AI 提问 (关键：将字符串转化为结构化 Task)
    for i, q in enumerate(questions):
        # 使用正则表达式快速识别常见类型（未来可升级为 LLM 识别）
        is_gp = ("爷爷" in q or "奶奶" in q or "祖父" in q or "外公" in q or "外婆" in q) and ("父系" in q or "母系" in q)
        
        if is_gp:
            name_match = re.search(r'^["“”]?(.+?)[即是]', q)
            detected_name = name_match.group(1).strip() if name_match else "该人物"
            is_gf = "爷" in q or "祖父" in q or "外公" in q
            
            task = InteractionTask(
                task_id=f"clarify_{i}",
                category=InteractionTaskCategory.CLARIFICATION,
                message=q
            )
            base_type = "grandfather" if is_gf else "grandmother"
            target_name_match = re.search(r'是(.+?)的', q)
            target_name = target_name_match.group(1).strip() if target_name_match else "该成员"
            
            paternal_label = f"确认为{'祖父' if is_gf else '祖母'} (父系)"
            maternal_label = f"确认为{'外祖父' if is_gf else '外祖母'} (母系)"
            
            task.add_option(
                paternal_label, 
                "RESOLVE_GRANDPARENT", 
                {"name": detected_name, "target_name": target_name, "base_type": base_type, "variant": "PATERNAL"}
            )
            task.add_option(
                maternal_label, 
                "RESOLVE_GRANDPARENT", 
                {"name": detected_name, "target_name": target_name, "base_type": base_type, "variant": "MATERNAL"}
            )
            tasks.append(task.to_dict())
        else:
            # 识别是/否问题，生成确认按钮
            # 检测常见的是/否疑问词
            is_yes_no_question = any([
                "吗？" in q,
                "是吗？" in q,
                "对吗？" in q,
                "是否" in q,
                "是不是" in q,
                "确认" in q,
                "确定" in q
            ])
            
            if is_yes_no_question:
                # 是/否问题，生成确认按钮
                task = InteractionTask(
                    task_id=f"q_{i}",
                    category=InteractionTaskCategory.CLARIFICATION,
                    message=q,
                    task_type=InteractionTaskType.YES_NO
                )
                task.add_option("确认", "CONFIRM", {})
                task.add_option("否定", "REJECT", {})
                tasks.append(task.to_dict())
            else:
                # 其他类型问题，转为文本输入
                task = InteractionTask(
                    task_id=f"q_{i}",
                    category=InteractionTaskCategory.CLARIFICATION,
                    message=q,
                    task_type=InteractionTaskType.INPUT_TEXT
                )
                task.add_option("提交修正", "SUBMIT_CLARIFICATION", {})
                tasks.append(task.to_dict())

    return tasks

def _apply_extraction_to_compiler(compiler: CompilerEngine, entities: List[Dict], relationships: List[Dict], events: List[Dict], record: bool = False):
    """
    通用逻辑：将 AI 提取（或用户确认）的数据转化为 Fact 并应用到编译器。
    实现了审计（模拟）与提交（物理执行）的逻辑复用。
    """
    family_id = compiler.family_id
    temp_to_real_id = {}
    
    # 1. 处理实体
    for ent in entities:
        # 判定是否为新人物：
        # 如果是提交阶段，看 ent["action"] == "CREATE"
        # 如果是审计阶段，看 ent["is_new"] == True
        is_create = ent.get("action") == "CREATE" or (ent.get("action") is None and ent.get("is_new") is True)
        
        if is_create:
            # [FIX] 检查是否有针对此人的性别修正决议
            gender_val = "male" if ent["gender"] in ["M", "male"] else ("female" if ent["gender"] in ["F", "female"] else "unknown")
            resolutions = getattr(compiler, "resolutions", {})
            for res in resolutions.values():
                if isinstance(res, str) and res.startswith("ACTION:MODIFY_GENDER"):
                    try:
                        payload = json.loads(res.split(":", 2)[2])
                        if payload.get("temp_id") == ent["temp_id"]:
                            gender_val = "male" if payload.get("gender") == "M" else "female"
                    except: pass

            # 审计阶段使用 temp_id 模拟，提交阶段使用新生成的 UUID
            person_id = f"person_{uuid.uuid4().hex[:8]}" if record else ent["temp_id"]
            compiler.apply_fact(FactLog(family_id, "ADD_NODE", {
                "id": person_id,
                "name": ent["name"],
                "gender": gender_val,
                "tags": ent.get("tags", []),
                "attributes": ent.get("attributes", {}),
                "notes": ent.get("notes")
            }), record=record)
            temp_to_real_id[ent["temp_id"]] = person_id
        else:
            # 关联已有人物
            real_id = ent.get("matched_db_id")
            if real_id:
                temp_to_real_id[ent["temp_id"]] = real_id
                # 提交阶段如果姓名有变，则更新
                if record:
                    existing_p = compiler.graph.get_person(real_id)
                    if existing_p and ent["name"] != existing_p.name:
                        compiler.apply_fact(FactLog(family_id, "UPDATE_NODE", {
                            "id": real_id,
                            "name": ent["name"]
                        }), record=True)

    # 建立一个临时名称映射，用于处理 AI 可能直接返回名字作为引用的情况
    name_to_id = {p.name: p.id for p in compiler.graph.people.values()}
    for ent in entities:
        if ent["temp_id"] in temp_to_real_id:
            name_to_id[ent["name"]] = temp_to_real_id[ent["temp_id"]]

    # 2. 处理关系
    resolutions = getattr(compiler, "resolutions", {})
    
    for i, rel in enumerate(relationships):
        # 检查是否有针对此关系的修正决议
        rel_key = f"rel_conflict_{i}"
        res_val = resolutions.get(rel_key, "")
        
        src_ref = rel["source_ref"]
        tgt_ref = rel["target_ref"]
        kinship_type = rel.get("kinship_type")
        
        # 应用修正逻辑
        if res_val.startswith("ACTION:SWAP_DIRECTION"):
            src_ref, tgt_ref = tgt_ref, src_ref # 交换方向
        elif res_val.startswith("ACTION:REJECT_EDGE"):
            continue # 跳过该错误关系
            
        src_id = temp_to_real_id.get(src_ref) or name_to_id.get(src_ref) or src_ref
        tgt_id = temp_to_real_id.get(tgt_ref) or name_to_id.get(tgt_ref) or tgt_ref
        
        desc = rel.get("natural_language_desc", "")
        
        if kinship_type:
            compiler.apply_fact(FactLog(family_id, "ADD_EDGE", {
                "person_a": src_id,
                "person_b": tgt_id,
                "type": kinship_type,
                "attributes": rel.get("attributes", {})
            }), record=record)
        else:
            # 降级逻辑
            base_type = "parent_child" if any(k in desc for k in ["父", "母", "爸", "妈", "子", "女", "孙", "侄", "甥"]) else "spouse"
            compiler.apply_fact(FactLog(family_id, "ADD_EDGE", {
                "person_a": src_id,
                "person_b": tgt_id,
                "type": base_type,
                "attributes": rel.get("attributes", {})
            }), record=record)

async def commit_ai_extraction(request_data: Dict[str, Any]):
    """
    提交确认逻辑：复用通用执行逻辑
    """
    family_id = request_data["family_id"]
    _log_pipeline_event(family_id, "COMMIT_START", request_data)
    
    summary_actions = []
    compiler = CompilerEngine(family_id)
    compiler.resolutions = request_data.get("resolutions", {})
    
    # 1. 加载并编译
    compiler.compile(load_facts(family_id))
    
    # 2. 应用确认后的数据（物理执行）
    _apply_extraction_to_compiler(
        compiler,
        request_data["confirmed_entities"],
        request_data["confirmed_relationships"],
        request_data["confirmed_events"],
        record=True
    )

    # 3. 处理解析方案和额外动作
    if request_data.get("resolutions"):
        for key, res_value in request_data["resolutions"].items():
            if res_value == "CREATE_NEW_PLACEHOLDER":
                # 获取该歧义关联的信息来创建占位符
                # 这里简单处理，实际可根据 key 找回 Ambiguity 对象
                p_id = f"placeholder_{uuid.uuid4().hex[:8]}"
                compiler.apply_fact(FactLog(family_id, "ADD_NODE", {
                    "id": p_id,
                    "name": "未知人物",
                    "is_placeholder": True,
                    "placeholder_reason": f"从歧义 {key} 手动创建"
                }), record=True)
                compiler.apply_fact(FactLog(family_id, "RESOLVE_AMBIGUITY", {"key": key, "target_id": p_id}), record=True)
            elif res_value.startswith("ACTION:"):
                # 格式: ACTION:type:json_payload
                parts = res_value.split(":", 2)
                if len(parts) >= 3:
                    action_type = parts[1]
                    try:
                        payload = json.loads(parts[2])
                        if action_type == "CREATE_PLACEHOLDER":
                            # 复合动作：创建一个占位节点并将其设为歧义的解
                            p_id = f"placeholder_{uuid.uuid4().hex[:8]}"
                            compiler.apply_fact(FactLog(family_id, "ADD_NODE", {
                                "id": p_id,
                                "name": payload.get("name", "未知人物"),
                                "gender": payload.get("gender", "unknown"),
                                "is_placeholder": True,
                                "placeholder_reason": f"从歧义 {key} 手动创建"
                            }), record=True)
                            compiler.apply_fact(FactLog(family_id, "RESOLVE_AMBIGUITY", {"key": key, "target_id": p_id}), record=True)
                        else:
                            compiler.apply_fact(FactLog(family_id, action_type, payload), record=True)
                    except Exception as e:
                        logger.error(f"无法解析或执行解析方案动作负载: {parts[2]}, Error: {e}")
            elif res_value == "REJECT":
                # 通用拒绝逻辑
                compiler.apply_fact(FactLog(family_id, "RESOLVE_AMBIGUITY", {"key": key, "target_id": "REJECTED"}), record=True)
            else:
                # 正常目标ID
                compiler.apply_fact(FactLog(family_id, "RESOLVE_AMBIGUITY", {"key": key, "target_id": res_value}), record=True)
    
    if request_data.get("extra_actions"):
        for act in request_data["extra_actions"]:
            compiler.apply_fact(FactLog(family_id, act.get("action", "ADD_EDGE"), act.get("payload", {})), record=True)

    # 4. 持久化
    if compiler.new_facts:
        _log_pipeline_event(family_id, "COMMIT_FACTS", [f.to_dict() for f in compiler.new_facts])
        append_facts(family_id, compiler.new_facts)
        # 记录关键动作到历史记录
        for f in compiler.new_facts:
            if f.action == "ADD_NODE":
                summary_actions.append(f"新增人物: {f.payload['name']}")
                record_action(family_id, "create_person", "person", f.payload["id"], f.payload["name"])
            elif f.action == "ADD_EDGE":
                summary_actions.append(f"建立关系")
        
    return summary_actions if summary_actions else ["完成数据同步"]

def find_mentioned_people(graph, text: str) -> List[Dict[str, Any]]:
    """在文本中查找可能提到的人物"""
    mentioned_ids = set()
    for p in graph.people.values():
        if p.name in text and len(p.name) >= 2:
            mentioned_ids.add(p.id)
            rels = graph.get_person_relationships(p.id)
            for r in rels:
                mentioned_ids.add(r.person1_id)
                mentioned_ids.add(r.person2_id)
    
    result = []
    for pid in list(mentioned_ids)[:20]:
        p = graph.get_person(pid)
        if p:
            result.append({
                "id": p.id,
                "name": p.name,
                "gender": "M" if p.gender == Gender.MALE else "F" if p.gender == Gender.FEMALE else "UNKNOWN",
                "relationship_summary": get_relationship_summary(graph, p.id)
            })
    return result