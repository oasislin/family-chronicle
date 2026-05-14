"""
家族编年史智能族谱系统 - FastAPI后端主应用 (Refactored v3.1)
Family Chronicle Intelligent Genealogy System - Modular Backend
"""

import sys
import uvicorn
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Path as APIPath
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# 路径配置
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "backend"))

from config import settings
from models import Gender, RelationshipType, EventType, DateAccuracy, Confidence
from schemas import (
    PersonCreate, PersonUpdate, EventCreate, RelationshipCreate,
    AIParseRequest, ConflictCheckRequest, ChatExtractRequest, ChatCommitRequest,
    TaskResolutionRequest,
    ApiResponse
)

# 导入业务服务
from fact_service import load_family_graph, generate_family_id
from ai_service import perform_ai_extraction, commit_ai_extraction, find_mentioned_people
from history import record_action, get_person_history, get_recent_history
from biography_engine import generate_biography_from_graph

# 创建FastAPI应用
app = FastAPI(
    title="家族编年史 API",
    description="智能族谱系统后端API - 模块化重构版",
    version="1.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置日志
logger.remove()
logger.add(sys.stderr, level=settings.LOG_LEVEL, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
logger.info("Family Chronicle Backend Started (Modular Architecture)")

# --- 基础路由 ---
@app.get("/", response_model=ApiResponse)
async def root():
    return ApiResponse(success=True, message="欢迎使用家族编年史智能族谱系统API")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/config", response_model=ApiResponse)
async def get_config():
    """获取后端配置（如默认加载的家族ID）"""
    return ApiResponse(success=True, message="获取配置成功", data={
        "default_family_id": settings.DEFAULT_FAMILY_ID,
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION
    })

# --- 人物管理 API ---
@app.get("/api/families/{family_id}/people", response_model=ApiResponse)
async def list_people(family_id: str, name: Optional[str] = None, show_placeholders: bool = False):
    try:
        graph = load_family_graph(family_id)
        people = [p.to_dict() for p in graph.people.values() if show_placeholders or not p.is_placeholder]
        if name:
            people = [p for p in people if name.lower() in p["name"].lower()]
        return ApiResponse(success=True, message=f"找到 {len(people)} 个人物", data=people)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/families/{family_id}/people/{person_id}", response_model=ApiResponse)
async def get_person(family_id: str, person_id: str):
    try:
        graph = load_family_graph(family_id)
        person = graph.get_person(person_id)
        if not person: raise HTTPException(status_code=404, detail="人物不存在")
        return ApiResponse(success=True, message="获取成功", data={
            "person": person.to_dict(),
            "relationships": [r.to_dict() for r in graph.get_person_relationships(person_id)],
            "events": [e.to_dict() for e in graph.get_person_events(person_id)]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/families/{family_id}/people/{person_id}", response_model=ApiResponse)
async def update_person(family_id: str, person_id: str, person_data: PersonUpdate):
    """更新人物信息"""
    try:
        graph = load_family_graph(family_id)
        person = graph.get_person(person_id)
        if not person: raise HTTPException(status_code=404, detail="人物不存在")
        for key, value in person_data.dict(exclude_unset=True).items():
            if key == "gender" and value: setattr(person, key, Gender(value))
            else: setattr(person, key, value)
        return ApiResponse(success=True, message="更新成功", data=person.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/families/{family_id}/people/{person_id}", response_model=ApiResponse)
async def delete_person(family_id: str, person_id: str):
    """删除人物"""
    try:
        return ApiResponse(success=True, message="删除功能暂请通过 Fact 记录手动处理")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/families/{family_id}/people/{person_id}/biography", response_model=ApiResponse)
async def regenerate_biography(family_id: str, person_id: str):
    """重新生成生平传记"""
    try:
        graph = load_family_graph(family_id)
        bio = generate_biography_from_graph(graph, person_id)
        return ApiResponse(success=True, message="生成成功", data={"story": bio})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 核心交互 API (AI Extraction) ---
@app.post("/api/chat/extract", response_model=ApiResponse)
async def chat_extract(request: ChatExtractRequest):
    """交互式提取：第一步，调用 AI Service"""
    try:
        result = await perform_ai_extraction(request.text, request.family_id)
        return ApiResponse(success=True, message="提取成功", data=result)
    except Exception as e:
        logger.error(f"Chat extract failed: {str(e)}")
        return ApiResponse(success=False, message=str(e))

@app.post("/api/chat/validate", response_model=ApiResponse)
async def chat_validate(request: ChatCommitRequest):
    """交互式提取：扩散验证，模拟当前选择并返回更新后的任务"""
    try:
        from ai_service import perform_ai_validation
        result = await perform_ai_validation(request.dict())
        return ApiResponse(success=True, message="扩散验证完成", data=result)
    except Exception as e:
        logger.error(f"Chat validate failed: {str(e)}")
        return ApiResponse(success=False, message=str(e))

@app.post("/api/chat/commit", response_model=ApiResponse)
async def chat_commit(request: ChatCommitRequest):
    """交互式提取：第二步，确认入库并触发推导引擎"""
    try:
        actions = await commit_ai_extraction(request.dict())
        return ApiResponse(success=True, message="数据确认已入库并触发推导", data={"actions": actions})
    except Exception as e:
        logger.error(f"Chat commit failed: {str(e)}")
        return ApiResponse(success=False, message=str(e))

# --- 家族管理 API ---
@app.post("/api/families", response_model=ApiResponse)
async def create_family(name: str = Query(..., description="家族名称")):
    try:
        family_id = generate_family_id()
        from fact_store import save_facts
        save_facts(family_id, [])
        return ApiResponse(success=True, message="家族创建成功", data={"family_id": family_id, "name": name})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/families", response_model=ApiResponse)
async def list_families():
    try:
        families = []
        DATA_DIR = settings.DATA_DIR
        for file in DATA_DIR.glob("*_facts.json"):
            if file.name == "_facts.json": continue
            family_id = file.name.replace("_facts.json", "")
            families.append({
                "family_id": family_id,
                "last_modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
        return ApiResponse(success=True, message=f"找到 {len(families)} 个家族", data=families)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 家族管理与导出 API ---
@app.get("/api/families/{family_id}/export", response_model=ApiResponse)
async def export_family_data(family_id: str):
    """导出全量家族数据（前端初始化必需）"""
    try:
        from ai_service import _unify_to_interaction_tasks
        graph = load_family_graph(family_id)
        data = graph.to_dict()
        # 补充前端需要的歧义信息和任务
        data["ambiguities"] = getattr(graph, "ambiguities", [])
        data["tasks"] = _unify_to_interaction_tasks(data["ambiguities"], [], [])
        return ApiResponse(success=True, message="导出成功", data=data)
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/families/{family_id}/resolve_task", response_model=ApiResponse)
async def resolve_task(family_id: str, request: TaskResolutionRequest):
    """处理前端提交的交互任务"""
    try:
        from fact_store import append_facts, FactLog, load_facts
        from compiler_engine import CompilerEngine
        
        payload = request.payload or {}
        if request.target_id:
            payload["target_id"] = request.target_id
        # 为了兼容 RESOLVE_AMBIGUITY，补充 key 字段
        if request.action == "RESOLVE_AMBIGUITY" and "key" not in payload:
            payload["key"] = request.task_id

        # 对于某些特例：比如忽略冲突，实际上不需要执行具体引擎动作，我们也可以记录下来
        fact = FactLog(family_id, request.action, payload)
        append_facts(family_id, [fact])
        
        # 触发重新推导
        facts = load_facts(family_id)
        engine = CompilerEngine(family_id)
        engine.compile(facts)
        
        return ApiResponse(success=True, message="任务处理成功，状态已更新", data={})
    except Exception as e:
        logger.error(f"Resolve task failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/families/{family_id}/relationships", response_model=ApiResponse)
async def list_relationships(family_id: str):
    """列出家族关系"""
    try:
        graph = load_family_graph(family_id)
        rels = [r.to_dict() for r in graph.relationships.values()]
        return ApiResponse(success=True, message="获取关系成功", data={
            "relationships": rels,
            "ambiguities": getattr(graph, "ambiguities", [])
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- AI 解析与意图识别 API ---
@app.post("/api/ai/detect-intent", response_model=ApiResponse)
async def detect_intent(request: AIParseRequest):
    """意图识别（如判断是否为合并指令）"""
    try:
        # 这里暂时简单返回，后续可接入 ai_service 的 detect 逻辑
        return ApiResponse(success=True, message="意图识别完成", data={"is_merge": False})
    except Exception as e:
        return ApiResponse(success=False, message=str(e))

# --- 历史记录 API ---
@app.get("/api/families/{family_id}/history", response_model=ApiResponse)
async def get_edit_history(family_id: str, person_id: Optional[str] = None, limit: int = 50):
    try:
        if person_id: records = get_person_history(family_id, person_id)
        else: records = get_recent_history(family_id, limit)
        return ApiResponse(success=True, message="获取历史成功", data=records)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("启动模块化重构版家族编年史API服务器...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")