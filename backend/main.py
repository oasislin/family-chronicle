"""
家族编年史智能族谱系统 - FastAPI后端主应用
Family Chronicle Intelligent Genealogy System - FastAPI Backend

提供RESTful API接口，处理家族数据管理、AI解析、冲突检测等功能。
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
import json
import re
from datetime import datetime
import os
from pathlib import Path

# 导入配置
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from models import FamilyGraph, Person, Event, Relationship, Gender, EventType, DateAccuracy, Confidence, RelationshipType
from prompt_engineering import FamilyParsingPrompt
from pypinyin import pinyin, lazy_pinyin, Style
from conflict_detector import ConflictDetector, check_conflicts

# 关系推导引擎 v2 — BFS 扩散式推导
from derivation_engine_v2 import derive_relationships_v2, get_sibling_type
from biography_engine import generate_biography_from_graph
from relationship_validator import validate_relationships, auto_fix_violations, validate_and_fix
from history import record_action, get_person_history, get_recent_history

# 导入后端配置
sys.path.append(str(Path(__file__).parent))
from config import settings, get_ai_provider_config

# 创建FastAPI应用
app = FastAPI(
    title="家族编年史 API",
    description="智能族谱系统后端API，提供家族数据管理、AI解析、冲突检测等功能",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# 初始化提示词管理器
prompt_manager = FamilyParsingPrompt()

# 配置日志
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger.remove()  # 移除默认处理器
logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
logger.add(LOG_DIR / "app.log", rotation="10 MB", level="DEBUG", encoding="utf-8")
logger.info("Family Chronicle Backend Started")

# Pydantic模型定义
class PersonCreate(BaseModel):
    name: str = Field(..., description="姓名")
    gender: Optional[str] = Field("unknown", description="性别: male, female, unknown")
    birth_date: Optional[str] = Field(None, description="出生日期")
    death_date: Optional[str] = Field(None, description="去世日期")
    birth_place: Optional[str] = Field(None, description="出生地")
    current_residence: Optional[str] = Field(None, description="现居住地")
    tags: Optional[List[str]] = Field([], description="标签列表")
    notes: Optional[str] = Field(None, description="备注")
    story: Optional[str] = Field(None, description="生平故事")

class PersonUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    death_date: Optional[str] = None
    birth_place: Optional[str] = None
    current_residence: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    story: Optional[str] = None

class EventCreate(BaseModel):
    type: str = Field(..., description="事件类型")
    description: str = Field(..., description="事件描述")
    date: Optional[str] = Field(None, description="事件日期")
    date_accuracy: Optional[str] = Field("unknown", description="日期精确度")
    location: Optional[str] = Field(None, description="事件地点")
    participants: Optional[List[Dict[str, str]]] = Field([], description="参与者列表")
    source: Optional[str] = Field(None, description="信息来源")
    confidence: Optional[str] = Field("medium", description="置信度")

class RelationshipCreate(BaseModel):
    person1_id: str = Field(..., description="第一个人物ID")
    person2_id: str = Field(..., description="第二个人物ID")
    type: str = Field(..., description="关系类型")
    subtype: Optional[str] = Field(None, description="关系子类型")
    start_date: Optional[str] = Field(None, description="关系开始日期")
    end_date: Optional[str] = Field(None, description="关系结束日期")
    attributes: Optional[Dict[str, Any]] = Field({}, description="关系属性")
    event_id: Optional[str] = Field(None, description="关联事件ID")
    notes: Optional[str] = Field(None, description="备注")

class AIParseRequest(BaseModel):
    text: str = Field(..., description="要解析的自然语言文本")
    family_id: Optional[str] = Field(None, description="家族ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    options: Optional[Dict[str, Any]] = Field({}, description="解析选项")

class ConflictCheckRequest(BaseModel):
    family_id: str = Field(..., description="家族ID")
    new_data: Dict[str, Any] = Field(..., description="新数据")

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# 辅助函数
def load_family_graph(family_id: str) -> FamilyGraph:
    """加载家族图谱数据"""
    file_path = DATA_DIR / f"{family_id}.json"
    if file_path.exists():
        try:
            return FamilyGraph.import_json(str(file_path))
        except Exception as e:
            print(f"警告: 家族文件 {file_path} 损坏，已跳过 ({str(e)})")
            return FamilyGraph()
    return FamilyGraph()

def save_family_graph(family_id: str, graph: FamilyGraph):
    """保存家族图谱数据"""
    file_path = DATA_DIR / f"{family_id}.json"
    graph.export_json(str(file_path))

def _get_rel_type_str(r) -> str:
    """获取关系的类型字符串（兼容Enum和String）"""
    if hasattr(r.type, 'value'):
        return r.type.value
    return str(r.type)

def generate_family_id() -> str:
    """生成家族ID"""
    return f"family_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# API路由
@app.get("/", response_model=ApiResponse)
async def root():
    """根路径"""
    return ApiResponse(
        success=True,
        message="欢迎使用家族编年史智能族谱系统API",
        data={
            "version": "1.0.0",
            "docs": "/api/docs",
            "endpoints": {
                "people": "/api/people",
                "events": "/api/events",
                "relationships": "/api/relationships",
                "ai_parse": "/api/ai/parse",
                "conflict_check": "/api/conflict/check"
            }
        }
    )

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# 人物管理API
@app.post("/api/families/{family_id}/people", response_model=ApiResponse)
async def create_person(
    family_id: str,
    person_data: PersonCreate = ...
):
    """创建新人物"""
    try:
        graph = load_family_graph(family_id)
        
        # 创建前检查重复
        dupes = _find_creation_duplicates(person_data.name, graph)
        if dupes and dupes[0][1] >= 0.8:
            return ApiResponse(
                success=False,
                message=f"发现疑似重复人物: {dupes[0][0].name} (相似度{dupes[0][1]})",
                data={
                    "duplicate_detected": True,
                    "candidates": [
                        {"id": m[0].id, "name": m[0].name, "score": m[1], "reason": m[2]}
                        for m in dupes[:5]
                    ],
                }
            )
        
        # 创建Person对象 - 将字符串转换为Gender枚举
        gender = Gender(person_data.gender) if person_data.gender else Gender.UNKNOWN
        person = Person(
            name=person_data.name,
            gender=gender
        )
        person.birth_date = person_data.birth_date
        person.death_date = person_data.death_date
        person.birth_place = person_data.birth_place
        person.current_residence = person_data.current_residence
        person.tags = person_data.tags or []
        person.notes = person_data.notes
        person.story = person_data.story
        
        # 添加到图谱
        person_id = graph.add_person(person)
        save_family_graph(family_id, graph)

        # 记录编辑历史
        record_action(
            family_id=family_id,
            action="create_person",
            target_type="person",
            target_id=person_id,
            target_name=person.name,
            after=person.to_dict(),
            summary=f"新增人物: {person.name}",
        )

        return ApiResponse(
            success=True,
            message=f"人物 '{person.name}' 创建成功",
            data={"person_id": person_id, "person": person.to_dict()}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建人物失败: {str(e)}")

@app.get("/api/families/{family_id}/people", response_model=ApiResponse)
async def list_people(
    family_id: str,
    name: Optional[str] = Query(None, description="按姓名搜索"),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    show_placeholders: Optional[bool] = Query(False, description="是否显示占位节点")
):
    """获取人物列表"""
    try:
        graph = load_family_graph(family_id)
        people = list(graph.people.values())
        
        # 过滤占位节点（默认隐藏）
        if not show_placeholders:
            people = [p for p in people if not p.is_placeholder]
        
        # 应用筛选
        if name:
            people = [p for p in people if name.lower() in p.name.lower()]
        if tag:
            people = [p for p in people if tag in p.tags]
        
        return ApiResponse(
            success=True,
            message=f"找到 {len(people)} 个人物",
            data=[p.to_dict() for p in people]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取人物列表失败: {str(e)}")

@app.get("/api/families/{family_id}/people/{person_id}", response_model=ApiResponse)
async def get_person(
    family_id: str,
    person_id: str
):
    """获取人物详情"""
    try:
        graph = load_family_graph(family_id)
        person = graph.get_person(person_id)
        
        if not person:
            raise HTTPException(status_code=404, detail="人物不存在")
        
        # 获取相关关系和事件
        relationships = graph.get_person_relationships(person_id)
        events = graph.get_person_events(person_id)
        
        return ApiResponse(
            success=True,
            message="获取人物详情成功",
            data={
                "person": person.to_dict(),
                "relationships": [r.to_dict() for r in relationships],
                "events": [e.to_dict() for e in events]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取人物详情失败: {str(e)}")

@app.delete("/api/families/{family_id}/people/{person_id}", response_model=ApiResponse)
async def delete_person(
    family_id: str,
    person_id: str
):
    """删除人物"""
    try:
        graph = load_family_graph(family_id)
        person = graph.get_person(person_id)
        
        if not person:
            raise HTTPException(status_code=404, detail="人物不存在")
        
        person_name = person.name
        
        # 删除相关的关系
        relationships_to_remove = [
            rel_id for rel_id, rel in graph.relationships.items()
            if rel.person1_id == person_id or rel.person2_id == person_id
        ]
        for rel_id in relationships_to_remove:
            del graph.relationships[rel_id]
        
        # 删除人物
        del graph.people[person_id]

        # 保存
        save_family_graph(family_id, graph)

        # 记录编辑历史
        record_action(
            family_id=family_id,
            action="delete_person",
            target_type="person",
            target_id=person_id,
            target_name=person_name,
            before={"name": person_name, "deleted_relationships": len(relationships_to_remove)},
            summary=f"删除人物: {person_name}（含 {len(relationships_to_remove)} 条关系）",
        )

        return ApiResponse(
            success=True,
            message=f"人物 '{person_name}' 已删除",
            data={"deleted_person_id": person_id, "deleted_relationships": len(relationships_to_remove)}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除人物失败: {str(e)}")


@app.put("/api/families/{family_id}/people/{person_id}", response_model=ApiResponse)
async def update_person(
    family_id: str,
    person_id: str,
    person_data: PersonUpdate = ...
):
    """更新人物信息"""
    try:
        graph = load_family_graph(family_id)
        person = graph.get_person(person_id)

        if not person:
            raise HTTPException(status_code=404, detail="人物不存在")

        # 捕获修改前状态
        before_state = person.to_dict()

        # 只更新提交的字段
        update_data = person_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if key == "gender" and value:
                setattr(person, key, Gender(value))
            else:
                setattr(person, key, value)

        person.updated_at = datetime.now().isoformat()
        save_family_graph(family_id, graph)

        # 记录编辑历史
        changed_fields = list(update_data.keys())
        record_action(
            family_id=family_id,
            action="update_person",
            target_type="person",
            target_id=person_id,
            target_name=person.name,
            before=before_state,
            after=person.to_dict(),
            summary=f"更新 {person.name}: {', '.join(changed_fields)}",
        )

        return ApiResponse(
            success=True,
            message=f"人物 '{person.name}' 更新成功",
            data={"person": person.to_dict()}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新人物失败: {str(e)}")


@app.post("/api/families/{family_id}/people/{person_id}/biography", response_model=ApiResponse)
async def regenerate_biography(
    family_id: str,
    person_id: str
):
    """为指定人物重新生成生平传记"""
    try:
        graph = load_family_graph(family_id)
        person = graph.get_person(person_id)
        if not person:
            raise HTTPException(status_code=404, detail="人物不存在")

        bio = generate_biography_from_graph(graph, person_id)
        if bio:
            person.story = bio
            person.updated_at = datetime.now().isoformat()
            save_family_graph(family_id, graph)

        return ApiResponse(
            success=True,
            message=f"人物 '{person.name}' 的传记已生成",
            data={"person_id": person_id, "story": bio or ""}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成传记失败: {str(e)}")


@app.post("/api/families/{family_id}/biography/batch", response_model=ApiResponse)
async def regenerate_all_biographies(
    family_id: str
):
    """为家族所有人物重新生成生平传记"""
    try:
        graph = load_family_graph(family_id)
        updated = []

        for person_id, person in graph.people.items():
            bio = generate_biography_from_graph(graph, person_id)
            if bio:
                person.story = bio
                person.updated_at = datetime.now().isoformat()
                updated.append(person.name)

        save_family_graph(family_id, graph)

        return ApiResponse(
            success=True,
            message=f"已为 {len(updated)} 位人物生成传记",
            data={"updated": updated}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量生成传记失败: {str(e)}")


@app.delete("/api/families/{family_id}/relationships/{rel_id}", response_model=ApiResponse)
async def delete_relationship(
    family_id: str,
    rel_id: str
):
    """删除关系"""
    try:
        graph = load_family_graph(family_id)

        if rel_id not in graph.relationships:
            raise HTTPException(status_code=404, detail="关系不存在")

        del graph.relationships[rel_id]
        save_family_graph(family_id, graph)

        return ApiResponse(success=True, message="关系已删除")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除关系失败: {str(e)}")


@app.get("/api/families/{family_id}/graph/ancestors/{person_id}", response_model=ApiResponse)
async def get_ancestors(family_id: str, person_id: str, max_depth: int = Query(10)):
    """查找祖先"""
    try:
        graph = load_family_graph(family_id)
        ancestors = graph.find_ancestors(person_id, max_depth)
        return ApiResponse(success=True, message=f"找到 {len(ancestors)} 位祖先", data=ancestors)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/families/{family_id}/graph/descendants/{person_id}", response_model=ApiResponse)
async def get_descendants(family_id: str, person_id: str, max_depth: int = Query(10)):
    """查找后代"""
    try:
        graph = load_family_graph(family_id)
        descendants = graph.find_descendants(person_id, max_depth)
        return ApiResponse(success=True, message=f"找到 {len(descendants)} 位后代", data=descendants)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/families/{family_id}/graph/path/{id1}/{id2}", response_model=ApiResponse)
async def get_shortest_path(family_id: str, id1: str, id2: str):
    """查找两人之间的最短路径"""
    try:
        graph = load_family_graph(family_id)
        path = graph.find_shortest_path(id1, id2)
        if path:
            return ApiResponse(success=True, message=f"找到路径，共 {path['length']} 步", data=path)
        return ApiResponse(success=False, message="未找到连接路径")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/families/{family_id}/graph/tree/{person_id}", response_model=ApiResponse)
async def get_family_tree(family_id: str, person_id: str, max_depth: int = Query(5)):
    """获取家族树"""
    try:
        graph = load_family_graph(family_id)
        tree = graph.get_family_tree(person_id, max_depth)
        if tree:
            return ApiResponse(success=True, message="获取家族树成功", data=tree)
        return ApiResponse(success=False, message="人物不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 事件管理API
@app.post("/api/families/{family_id}/events", response_model=ApiResponse)
async def create_event(
    family_id: str,
    event_data: EventCreate = ...
):
    """创建新事件"""
    try:
        graph = load_family_graph(family_id)
        
        # 创建Event对象 - 将字符串转换为枚举
        event_type = EventType(event_data.type) if event_data.type else EventType.OTHER
        event = Event(
            event_type=event_type,
            description=event_data.description
        )
        event.date = event_data.date
        event.date_accuracy = DateAccuracy(event_data.date_accuracy) if event_data.date_accuracy else DateAccuracy.UNKNOWN
        event.location = event_data.location
        event.participants = event_data.participants or []
        event.source = event_data.source
        event.confidence = Confidence(event_data.confidence) if event_data.confidence else Confidence.MEDIUM
        
        # 添加到图谱
        event_id = graph.add_event(event)
        save_family_graph(family_id, graph)
        
        return ApiResponse(
            success=True,
            message=f"事件 '{event.description}' 创建成功",
            data={"event_id": event_id, "event": event.to_dict()}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建事件失败: {str(e)}")

@app.get("/api/families/{family_id}/events", response_model=ApiResponse)
async def list_events(
    family_id: str,
    type: Optional[str] = Query(None, description="按事件类型筛选"),
    year: Optional[int] = Query(None, description="按年份筛选")
):
    """获取事件列表"""
    try:
        graph = load_family_graph(family_id)
        events = list(graph.events.values())
        
        # 应用筛选
        if type:
            events = [e for e in events if e.type == type]
        if year:
            events = [e for e in events if e.date and str(year) in e.date]
        
        return ApiResponse(
            success=True,
            message=f"找到 {len(events)} 个事件",
            data=[e.to_dict() for e in events]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取事件列表失败: {str(e)}")

# 关系管理API
@app.post("/api/families/{family_id}/relationships", response_model=ApiResponse)
async def create_relationship(
    family_id: str,
    rel_data: RelationshipCreate = ...
):
    """创建新关系"""
    try:
        graph = load_family_graph(family_id)
        
        # 验证人物是否存在
        if not graph.get_person(rel_data.person1_id):
            raise HTTPException(status_code=404, detail=f"人物 {rel_data.person1_id} 不存在")
        if not graph.get_person(rel_data.person2_id):
            raise HTTPException(status_code=404, detail=f"人物 {rel_data.person2_id} 不存在")
        
        # 创建Relationship对象 - 将字符串转换为枚举
        rel_type = RelationshipType(rel_data.type) if rel_data.type else RelationshipType.OTHER
        relationship = Relationship(
            person1_id=rel_data.person1_id,
            person2_id=rel_data.person2_id,
            rel_type=rel_type
        )
        relationship.subtype = rel_data.subtype
        relationship.start_date = rel_data.start_date
        relationship.end_date = rel_data.end_date
        relationship.attributes = rel_data.attributes or {}
        relationship.event_id = rel_data.event_id
        relationship.notes = rel_data.notes
        
        # 添加到图谱
        rel_id = graph.add_relationship(relationship)
        
        # BFS 扩散式关系推导
        from derivation_engine import propagate_from_nodes
        derived = propagate_from_nodes(graph, {rel_data.person1_id, rel_data.person2_id})
        
        save_family_graph(family_id, graph)
        
        return ApiResponse(
            success=True,
            message="关系创建成功",
            data={
                "relationship_id": rel_id,
                "relationship": relationship.to_dict(),
                "derived_relationships": len(derived),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建关系失败: {str(e)}")

@app.get("/api/families/{family_id}/relationships", response_model=ApiResponse)
async def list_relationships(
    family_id: str,
    person_id: Optional[str] = Query(None, description="按人物ID筛选"),
    type: Optional[str] = Query(None, description="按关系类型筛选")
):
    """获取关系列表"""
    try:
        graph = load_family_graph(family_id)
        relationships = list(graph.relationships.values())
        
        # 应用筛选
        if person_id:
            relationships = [r for r in relationships 
                           if r.person1_id == person_id or r.person2_id == person_id]
        if type:
            relationships = [r for r in relationships if r.type == type]
        
        return ApiResponse(
            success=True,
            message=f"找到 {len(relationships)} 个关系",
            data=[r.to_dict() for r in relationships]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取关系列表失败: {str(e)}")

# AI解析API
@app.post("/api/ai/parse", response_model=ApiResponse)
async def ai_parse_text(request: AIParseRequest):
    """使用AI解析自然语言文本"""
    try:
        # 1. 获取背景上下文 (最近活跃的人物)
        context_people = []
        if request.family_id:
            try:
                recent_history = get_recent_history(request.family_id, limit=20)
                # 提取最近涉及的人物ID
                recent_person_ids = []
                for record in reversed(recent_history):
                    pid = record.get("target_id")
                    if pid and record.get("target_type") == "person" and pid not in recent_person_ids:
                        recent_person_ids.append(pid)
                    if len(recent_person_ids) >= 10:
                        break
                
                # 加载这些人物的详细信息
                if recent_person_ids:
                    graph = load_family_graph(request.family_id)
                    for pid in recent_person_ids:
                        person = graph.get_person(pid)
                        if person:
                            context_people.append({
                                "name": person.name,
                                "gender": person.gender.value if hasattr(person.gender, 'value') else person.gender,
                                "tags": person.tags
                            })
                if context_people:
                    logger.info(f"AI Parse Context: {', '.join([p['name'] for p in context_people])}")
            except Exception as e:
                logger.warning(f"Failed to load context for AI parse: {e}")

        # 获取提示词
        messages = prompt_manager.get_parsing_prompt(request.text, context_people=context_people)
        
        # 获取AI提供商配置
        provider_config = get_ai_provider_config()
        
        # 检查是否有API密钥
        if not provider_config.get("api_key"):
            logger.warning("No AI API key found, falling back to simple parse")
            # 没有API密钥，使用本地简单解析
            parsed_data = _simple_parse(request.text)
            return ApiResponse(
                success=True,
                message="AI解析完成（本地简单解析，未配置AI API密钥）",
                data={
                    "parsed_data": parsed_data,
                    "prompt_used": {
                        "system": messages[0]["content"][:100] + "...",
                        "user": messages[1]["content"][:100] + "..."
                    }
                }
            )
        
        # 调用实际的AI API
        import httpx
        
        ai_provider = settings.AI_PROVIDER
        logger.info(f"Calling AI Provider: {ai_provider} for text: {request.text[:50]}...")
        
        if ai_provider == "deepseek":
            url = f"{provider_config['base_url']}/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider_config['api_key']}"
            }
            payload = {
                "model": provider_config["model"],
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 2000
            }
        elif ai_provider == "zhipu":
            url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider_config['api_key']}"
            }
            payload = {
                "model": provider_config["model"],
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 2000
            }
        elif ai_provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider_config['api_key']}"
            }
            payload = {
                "model": provider_config["model"],
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 2000
            }
        else:
            # 默认使用简单解析
            parsed_data = _simple_parse(request.text)
            return ApiResponse(
                success=True,
                message="AI解析完成（本地简单解析）",
                data={
                    "parsed_data": parsed_data,
                    "prompt_used": {
                        "system": messages[0]["content"][:100] + "...",
                        "user": messages[1]["content"][:100] + "..."
                    }
                }
            )
        
        # 调用AI API
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 解析响应
            content = result["choices"][0]["message"]["content"]
            logger.debug(f"AI Raw Content: {content}")
            
            # 尝试解析JSON
            import json
            try:
                # 提取JSON部分
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0]
                else:
                    json_str = content
                
                parsed_data = json.loads(json_str)
                logger.info(f"AI Parsed Success: {len(parsed_data.get('entities', []))} entities, {len(parsed_data.get('relationships', []))} relationships")
            except json.JSONDecodeError:
                # JSON解析失败，使用简单解析
                parsed_data = _simple_parse(request.text)
                parsed_data["metadata"]["ai_raw_response"] = content[:500]
        
        return ApiResponse(
            success=True,
            message="AI解析完成",
            data={
                "parsed_data": parsed_data,
                "prompt_used": {
                    "system": messages[0]["content"][:100] + "...",
                    "user": messages[1]["content"][:100] + "..."
                }
            }
        )
    except Exception as e:
        # 出错时回退到简单解析
        parsed_data = _simple_parse(request.text)
        parsed_data["metadata"]["error"] = str(e)
        return ApiResponse(
            success=True,
            message="AI解析完成（简单解析，AI服务出错）",
            data={
                "parsed_data": parsed_data,
                "prompt_used": {
                    "system": messages[0]["content"][:100] + "...",
                    "user": messages[1]["content"][:100] + "..."
                }
            }
        )


# 意图检测：判断用户输入是否是"合并同一个人"的指令
@app.post("/api/ai/detect-intent", response_model=ApiResponse)
async def detect_merge_intent(request: AIParseRequest):
    """用AI判断用户输入是否表达'两个人其实是同一个人'的合并意图"""
    import httpx
    import json as _json

    provider_config = get_ai_provider_config()
    if not provider_config.get("api_key"):
        # 没有AI，回退到不检测
        return ApiResponse(success=True, message="无AI服务", data={"is_merge": False})

    ai_provider = settings.AI_PROVIDER
    system_prompt = """你是意图分类器。分析用户输入，判断意图并提取人名。

输出格式（严格JSON）：
{"intent": "merge" | "relationship" | "info" | "other", "names": ["名字1", "名字2"]}

意图定义：
- merge: 用户表达"两个人是同一个人"或"需要合并"。信号词："就是"、"其实是"、"也叫"、"又叫"、"又名"、"搞错了"、"同一个人"、"合并"、"重复了"、"写错了"、"应该是"（指同一人）
- relationship: 用户在描述人与人之间的关系。信号词："爸爸"、"妈妈"、"丈夫"、"妻子"、"儿子"、"女儿"、"兄弟"、"姐妹"、"爷爷"、"奶奶"、"外公"、"外婆"、"叔叔"、"舅舅"、"姑姑"、"阿姨"、"娶了"、"嫁给"、"生了"、"领养"
- info: 用户在描述某人的信息（出生、死亡、职业、住址等），不涉及两人关系或合并
- other: 其他

关键判断规则：
- "A的爸爸叫B" → relationship（不是merge！这是在说B是A的父亲）
- "A的妈妈叫B" → relationship
- "A就是B" / "A也叫B" / "A和B是同一个人" → merge
- "A娶了B" / "A嫁给B" → relationship

提取规则：
- 提取所有人名（2-4个中文字符的专有名称）
- 不要提取关系称谓本身（如"爸爸"不是人名）
- 如果没有提到任何人，返回{"intent": "other", "names": []}
- 只返回JSON，不要任何解释"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.text}
    ]

    if ai_provider == "deepseek":
        url = f"{provider_config['base_url']}/v1/chat/completions"
    elif ai_provider == "zhipu":
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    elif ai_provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
    else:
        return ApiResponse(success=True, message="不支持的AI服务", data={"is_merge": False})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {provider_config['api_key']}"
    }
    payload = {
        "model": provider_config["model"],
        "messages": messages,
        "temperature": 0,
        "max_tokens": 200
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # 提取JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                json_str = content.strip()

            intent = _json.loads(json_str)
            print(f"[DEBUG detect-intent] text={request.text!r} → raw={content!r} → parsed={intent}")

            # 判断是否为合并意图：AI判定为merge，且恰好两个名字在数据库中都能找到
            intent_type = intent.get("intent", "other")
            names = intent.get("names", [])
            if intent_type == "merge" and len(names) == 2:
                name_a, name_b = names[0], names[1]
                # 验证两人都在数据库中
                if request.family_id:
                    graph = load_family_graph(request.family_id)
                    people = list(graph.people.values())
                    found_a = [p for p in people if p.name == name_a or p.name.startswith(name_a + ' ')]
                    found_b = [p for p in people if p.name == name_b or p.name.startswith(name_b + ' ')]
                    if len(found_a) >= 1 and len(found_b) >= 1 and found_a[0].id != found_b[0].id:
                        return ApiResponse(success=True, message="意图识别完成", data={
                            "is_merge": True, "name_a": name_a, "name_b": name_b
                        })

            return ApiResponse(success=True, message="意图识别完成", data={"is_merge": False})
    except Exception as e:
        return ApiResponse(success=True, message=f"意图识别失败: {e}", data={"is_merge": False})


def _simple_parse(text: str) -> Dict[str, Any]:
    """简单的本地解析（当没有AI API时使用）"""
    import re
    
    entities = []
    events = []
    relationships = []
    
    # 提取人名（简单匹配中文名字）
    name_patterns = [
        r'(?:叫|是|有)[\u4e00-\u9fa5]{2,4}',
        r'[\u4e00-\u9fa5]{2,4}(?:出生|结婚|认|生病|搬家|去世)',
        r'(?:老大|老二|老三|长子|次子|女儿)[\u4e00-\u9fa5]{2,4}',
        r'[\u4e00-\u9fa5]{2,4}(?:大爷|叔叔|阿姨|婶婶|舅舅|姑姑)',
    ]
    
    found_names = set()
    for pattern in name_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # 提取名字部分
            name = re.sub(r'^(?:叫|是|有|老大|老二|老三|长子|次子|女儿)', '', match)
            name = re.sub(r'(?:出生|结婚|认|生病|搬家|去世|大爷|叔叔|阿姨|婶婶|舅舅|姑姑)$', '', name)
            if len(name) >= 2 and name not in found_names:
                found_names.add(name)
    
    # 如果没有找到名字，尝试找所有2-4字的中文词
    if not found_names:
        all_names = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
        # 过滤掉常见词汇
        common_words = {'出生', '结婚', '生病', '搬家', '去世', '认了', '是', '有', '在', '于', '的', '了', '和'}
        found_names = {n for n in all_names if n not in common_words and len(n) >= 2}
    
    # 创建实体
    for i, name in enumerate(list(found_names)[:10]):  # 最多10个人
        gender = "male"  # 默认
        if any(f in name for f in ['梅', '芳', '丽', '红', '英', '娟', '玲', '敏', '静', '燕']):
            gender = "female"
        
        entities.append({
            "type": "person",
            "name": name,
            "temp_id": f"temp_person_{i+1:03d}",
            "gender": gender,
            "tags": [],
            "confidence": "medium"
        })
    
    # 提取事件
    event_patterns = [
        (r'(\d{4})年?.*?出生', 'birth'),
        (r'出生.*?(\d{4})年?', 'birth'),
        (r'(\d{4})年?.*?结婚', 'marriage'),
        (r'结婚.*?(\d{4})年?', 'marriage'),
        (r'认.*?做干爹', 'recognition'),
        (r'认了.*?干爹', 'recognition'),
        (r'(\d{4})年?.*?去世', 'death'),
        (r'去世.*?(\d{4})年?', 'death'),
    ]
    
    for pattern, event_type in event_patterns:
        match = re.search(pattern, text)
        if match:
            date = match.group(1) if match.lastindex else None
            events.append({
                "type": event_type,
                "description": match.group(0),
                "date": date,
                "date_accuracy": "year" if date else "unknown",
                "participants": [],
                "confidence": "medium"
            })
    
    return {
        "entities": entities,
        "events": events,
        "relationships": relationships,
        "metadata": {
            "parsing_confidence": 0.5 if entities else 0.1,
            "ambiguous_references": [],
            "suggested_questions": ["这是本地简单解析，建议配置AI API密钥获得更好的解析效果"] if not entities else []
        }
    }

@app.get("/api/ai/prompt")
async def get_parsing_prompt(text: str = Query(..., description="要解析的文本")):
    """获取解析提示词（用于调试）"""
    try:
        messages = prompt_manager.get_parsing_prompt(text)
        return ApiResponse(
            success=True,
            message="获取提示词成功",
            data={
                "system_prompt": messages[0]["content"],
                "user_prompt": messages[1]["content"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提示词失败: {str(e)}")

# 冲突检测API
@app.post("/api/conflict/check", response_model=ApiResponse)
async def check_conflicts_api(request: ConflictCheckRequest):
    """检查数据冲突 - 支持三种级别: 🟢无冲突 🟡语义模糊 🔴逻辑冲突"""
    try:
        graph = load_family_graph(request.family_id)
        new_data = request.new_data
        
        # 使用完整的冲突检测引擎
        result = check_conflicts(graph, new_data)
        
        return ApiResponse(
            success=True,
            message=result["summary"],
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"冲突检测失败: {str(e)}")


@app.post("/api/conflict/check-batch", response_model=ApiResponse)
async def check_conflicts_batch(
    family_id: str = Query(..., description="家族ID"),
    data_list: List[Dict[str, Any]] = ...
):
    """批量检查多组数据的冲突"""
    try:
        graph = load_family_graph(family_id)
        results = []
        
        for i, new_data in enumerate(data_list):
            result = check_conflicts(graph, new_data)
            results.append({
                "index": i,
                **result
            })
        
        # 统计汇总
        total_blocking = sum(1 for r in results if r["has_blocking"])
        total_ambiguous = sum(1 for r in results if r["has_ambiguous"])
        total_clean = sum(1 for r in results if not r["has_conflicts"])
        
        return ApiResponse(
            success=True,
            message=f"批量检测完成: {total_clean} 组无冲突, {total_ambiguous} 组需澄清, {total_blocking} 组有阻断",
            data={
                "results": results,
                "summary": {
                    "total": len(results),
                    "clean": total_clean,
                    "ambiguous": total_ambiguous,
                    "blocking": total_blocking
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量冲突检测失败: {str(e)}")


@app.get("/api/conflict/types")
async def get_conflict_types():
    """获取所有支持的冲突类型"""
    from conflict_detector import ConflictType, ConflictLevel
    
    return ApiResponse(
        success=True,
        message="获取冲突类型成功",
        data={
            "levels": [
                {"value": "none", "label": "🟢 无冲突", "description": "数据验证通过，可直接入库"},
                {"value": "ambiguous", "label": "🟡 语义模糊", "description": "需要用户手动确认"},
                {"value": "blocking", "label": "🔴 逻辑冲突", "description": "数据矛盾，需修正后方可入库"}
            ],
            "types": [
                {"value": t.value, "name": t.name} for t in ConflictType
            ]
        }
    )

# 自动导入API（核心：一件半事理念）
class AutoImportRequest(BaseModel):
    parsed_data: Dict[str, Any] = Field(..., description="AI解析结果")
    answers: Optional[Dict[str, str]] = Field(None, description="用户对提问的回答 {question_id: answer_value}")

def _get_pinyin_str(name: str) -> str:
    """获取纯字母拼音字符串"""
    if not name: return ""
    return "".join(lazy_pinyin(name))

def _split_chinese_name(name: str) -> tuple:
    """尝试将中文名拆分为(姓, 名)"""
    if not name or len(name) < 2:
        return name, ""
    
    # 常见复姓
    double_surnames = {"欧阳", "上官", "皇甫", "司马", "诸葛", "东方", "独孤", "南宫", "万俟", "夏侯"}
    if len(name) >= 3 and name[:2] in double_surnames:
        return name[:2], name[2:]
    
    # 默认单姓
    return name[0], name[1:]

def _fuzzy_match(name: str, people, gender: str = "unknown") -> list:
    """模糊匹配人物姓名，返回 [(person, score)] 列表"""
    results = []
    name_lower = name.lower().strip()
    name_is_kinship = _is_kinship_description(name)
    name_pinyin = _get_pinyin_str(name_lower)
    name_surname, name_given = _split_chinese_name(name_lower)
    
    for p in people:
        p_names = [p.name]
        # 添加别名
        p_names.extend(getattr(p, 'aliases', []) or [])
        
        best_p_score = 0
        
        # 性别校验
        gender_mismatch = False
        if gender != "unknown" and p.gender and p.gender != Gender.UNKNOWN:
            p_gender_val = p.gender.value if hasattr(p.gender, 'value') else str(p.gender)
            if p_gender_val != gender:
                gender_mismatch = True

        for current_name in p_names:
            p_name_lower = current_name.lower().strip()
            p_pinyin = _get_pinyin_str(p_name_lower)
            p_surname, p_given = _split_chinese_name(p_name_lower)
            
            score = 0
            
            # 1. 精确匹配
            if p_name_lower == name_lower:
                score = 1.0
            
            # 2. 拼音完全相同（同音字）
            elif p_pinyin == name_pinyin and len(name_pinyin) > 1:
                score = 0.95
                
            # 3. 姓相同，名拼音相同
            elif p_surname == name_surname and _get_pinyin_str(p_given) == _get_pinyin_str(name_given) and name_given:
                score = 0.92
            
            # 4. 包含匹配
            elif name_lower in p_name_lower or p_name_lower in name_lower:
                if name_is_kinship:
                    score = 0.3
                else:
                    score = 0.9
            
            # 5. 编辑距离
            else:
                dist = _levenshtein(name_lower, p_name_lower)
                if dist <= 1:
                    score = 0.80
                
            # 性别不匹配惩罚
            if gender_mismatch and score > 0.4:
                score *= 0.5
                
            if score > best_p_score:
                best_p_score = score
        
        if best_p_score > 0.1:
            results.append((p, best_p_score))
            
    return sorted(results, key=lambda x: -x[1])


# 常见称呼/昵称后缀
_NICKNAME_SUFFIXES = ('大爷', '大叔', '大伯', '叔叔', '阿姨', '婶婶', '舅舅',
                      '姑姑', '爷爷', '奶奶', '哥', '姐', '弟', '妹')

# 亲属称谓词（用于检测"XXX的大伯"这类描述性名称，不是真正的名字）
_KINSHIP_TERMS = ('爸爸', '妈妈', '父亲', '母亲', '爷爷', '奶奶', '外公', '外婆',
                  '大伯', '二伯', '叔叔', '舅舅', '姑姑', '姨妈', '姨', '伯',
                  '哥哥', '姐姐', '弟弟', '妹妹', '大哥', '大姐', '大弟',
                  '堂兄', '堂弟', '堂姐', '堂妹', '表兄', '表弟', '表姐', '表妹',
                  '堂兄弟', '表兄弟', '堂姐妹', '表姐妹',
                  '丈夫', '妻子', '老婆', '老公', '配偶',
                  '儿子', '女儿', '孙子', '孙女', '侄子', '侄女', '外甥', '外甥女',
                  '儿媳', '女婿', '嫂子', '弟媳', '姐夫', '妹夫',
                  '岳父', '岳母', '公公', '婆婆', '丈人', '丈母娘',
                  '大舅', '小舅', '大姑', '小姑', '大姨', '小姨',
                  '曾祖父', '曾祖母', '太爷爷', '太奶奶',
                  '祖父', '祖母', '外祖父', '外祖母',
                  '堂叔', '堂伯', '表叔', '表伯')

def _is_kinship_description(name: str) -> bool:
    """检测是否为亲属关系描述（如「王建国的大伯」），而非正式姓名"""
    # 包含「的」+ 亲属称谓 → 肯定是描述
    if '的' in name:
        return True
    # 亲属称谓后面跟着字母、数字、或编号后缀（如「曾祖母B」「大哥甲」「爷爷1」）
    # → 这是用户刻意的临时命名，不是纯描述，应视为名字
    import re
    for term in _KINSHIP_TERMS:
        if term in name:
            # 检查称谓后面是否跟了编号后缀
            suffix = name[name.index(term) + len(term):]
            if suffix and re.match(r'^[A-Za-z0-9\u4e00-\u4fff\u3400-\u4dbf]$', suffix):
                # 单个字母/数字/生僻字后缀 → 用户命名，不算描述
                return False
            return True
    return False

def _is_nickname(name: str) -> bool:
    """判断是否为称呼/昵称（非正式全名）"""
    return any(name.endswith(s) for s in _NICKNAME_SUFFIXES) or len(name) <= 2


_KINSHIP_KEYWORDS = [
    "曾祖父", "曾祖母", "高祖父", "高祖母",
    "祖父", "祖母", "爷爷", "奶奶", "外公", "外婆",
    "父亲", "母亲", "爸爸", "妈妈", "爸", "妈",
    "伯父", "伯母", "叔叔", "婶婶", "姑姑", "姑父",
    "舅舅", "舅妈", "姨妈", "姨父",
    "哥哥", "姐姐", "弟弟", "妹妹", "兄", "姐", "弟", "妹",
    "丈夫", "妻子", "老婆", "老公", "配偶",
    "儿子", "女儿", "儿媳", "女婿",
    "孙子", "孙女", "外孙", "外孙女",
    "侄子", "侄女", "外甥", "外甥女",
    "大伯", "小叔", "堂兄", "表兄", "表姐", "堂姐",
]


def _extract_kinship_roles(name: str) -> set:
    """从名称中提取亲属角色关键词"""
    roles = set()
    for kw in _KINSHIP_KEYWORDS:
        if kw in name:
            roles.add(kw)
    return roles


# ═══════════════════════════════════════════════════════════
# 占位节点管理（遮罩层核心逻辑）
# ═══════════════════════════════════════════════════════════

def get_or_create_parent_placeholder(graph, child_id: str, lineage: str, parent_gender: str, reason: str = ""):
    """
    查找或创建父母占位节点
    
    graph: FamilyGraph
    child_id: 子女ID
    lineage: "paternal" (父系) 或 "maternal" (母系)
    parent_gender: "male" 或 "female"
    reason: 占位原因
    
    返回: (Person, is_new) 元组
    """
    child = graph.get_person(child_id)
    if not child:
        return None, False
    
    # 1. 检查是否已有占位（同一孩子+同性别父母 → 复用）
    for p in graph.people.values():
        if p.is_placeholder and p.gender == Gender(parent_gender):
            # 占位名称格式: "{child_name}的爸爸/妈妈"
            term = "妈妈" if parent_gender == "female" else "爸爸"
            expected_name = f"{child.name}的{term}"
            if p.name == expected_name:
                return p, False
            # 也检查包含关系
            if child.name in p.name and term in p.name:
                return p, False
    
    # 2. 检查是否已有真实的父母（同性别）
    for rel in graph.relationships.values():
        if _get_rel_type_str(rel) == "parent_child":
            parent = graph.get_person(rel.person1_id)
            if parent and rel.person2_id == child_id and parent.gender == Gender(parent_gender):
                if not parent.is_placeholder:
                    return parent, False
    
    # 3. 创建新占位
    term = "妈妈" if parent_gender == "female" else "爸爸"
    placeholder = Person(
        name=f"{child.name}的{term}",
        gender=Gender(parent_gender),
    )
    placeholder.is_placeholder = True
    placeholder.placeholder_reason = reason or f"{child.name}的{lineage}系{term}占位"
    graph.add_person(placeholder)
    
    # 创建 parent_child 边: placeholder → child
    graph.add_relationship(Relationship(placeholder.id, child_id, RelationshipType.PARENT_CHILD, is_inferred=True))
    
    return placeholder, True


def get_or_create_grandparent_placeholder(graph, grandchild_id: str, lineage: str, gp_gender: str, reason: str = ""):
    """
    查找或创建祖父母占位节点（通过中间代占位链）
    
    返回: (grandparent_placeholder, is_new)
    """
    gc = graph.get_person(grandchild_id)
    if not gc:
        return None, False
    
    # 1. 先确保中间代占位存在
    # 外公/外婆 → 母系 → 通过妈妈
    # 爷爷/奶奶 → 父系 → 通过爸爸
    inter_gender = "female" if lineage == "maternal" else "male"
    inter_parent, inter_is_new = get_or_create_parent_placeholder(
        graph, grandchild_id, lineage, inter_gender,
        reason=f"中间代占位(为{reason})"
    )
    if not inter_parent:
        return None, False
    
    # 2. 再为中间代创建其父母占位（即祖父母）
    gp, gp_is_new = get_or_create_parent_placeholder(
        graph, inter_parent.id, lineage, gp_gender,
        reason=reason
    )
    return gp, inter_is_new or gp_is_new


def replace_placeholder_with_real(graph, placeholder_id: str, real_person) -> bool:
    """
    用真实人物替换占位节点
    
    1. 收集占位的所有关系
    2. 从图中删除占位和其关系
    3. 用真实人物ID重新创建关系
    """
    placeholder = graph.get_person(placeholder_id)
    if not placeholder or not placeholder.is_placeholder:
        return False
    
    # 1. 收集需要转移的关系
    rels_to_transfer = []
    rels_to_remove = []
    for rel in list(graph.relationships.values()):
        if rel.person1_id == placeholder_id or rel.person2_id == placeholder_id:
            rels_to_remove.append(rel.id)
            # 确定另一端
            other_id = rel.person2_id if rel.person1_id == placeholder_id else rel.person1_id
            if other_id == real_person.id:
                continue  # 自引用 → 跳过
            # 确定新关系的方向
            if rel.person1_id == placeholder_id:
                new_p1, new_p2 = real_person.id, other_id
            else:
                new_p1, new_p2 = other_id, real_person.id
            rels_to_transfer.append((new_p1, new_p2, rel.type))
    
    # 2. 删除旧关系和占位节点
    for rid in rels_to_remove:
        if rid in graph.relationships:
            del graph.relationships[rid]
    if placeholder_id in graph.people:
        del graph.people[placeholder_id]
    
    # 3. 用真实人物ID重新创建关系
    for new_p1, new_p2, rel_type in rels_to_transfer:
        # 检查是否已有相同关系（去重）
        existing = any(
            (r.person1_id == new_p1 and r.person2_id == new_p2 and r.type == rel_type) or
            (r.person1_id == new_p2 and r.person2_id == new_p1 and r.type == rel_type)
            for r in graph.relationships.values()
        )
        if not existing:
            new_rel = Relationship(new_p1, new_p2, rel_type)
            graph.add_relationship(new_rel)
    
    # 4. 合并别名
    if not hasattr(real_person, 'aliases'):
        real_person.aliases = []
    if placeholder.name not in real_person.aliases:
        real_person.aliases.append(placeholder.name)
    
    # 5. 重新生成受影响节点的传记
    from biography_engine import generate_biography_from_graph
    affected_nodes = {real_person.id}
    for new_p1, new_p2, _ in rels_to_transfer:
        affected_nodes.add(new_p1)
        affected_nodes.add(new_p2)
        
    for node_id in affected_nodes:
        node = graph.get_person(node_id)
        if node:
            node.story = generate_biography_from_graph(graph, node_id)
    
    return True


def _auto_create_grandparent_spouse(graph, gp_person, inter_child, lineage, actions, newly_created_ids):
    """
    自动为祖父母创建配偶（通过同一个中间代节点）
    
    当创建「外婆」→ 妈妈(占位) 时，自动创建「外公」→ 妈妈(占位)
    这样外婆和外公通过同一个妈妈节点自然成为配偶（Rule 5 推导）
    """
    GRANDPARENT_SPOUSE_MAP = {
        "外婆": ("外公", "male"),
        "外公": ("外婆", "female"),
        "爷爷": ("奶奶", "female"),
        "奶奶": ("爷爷", "male"),
        "外祖母": ("外祖父", "male"),
        "外祖父": ("外祖母", "female"),
        "祖父": ("祖母", "female"),
        "祖母": ("祖父", "male"),
    }
    
    gp_name = gp_person.name
    counterpart_name = None
    counterpart_gender = None
    for keyword, (counterpart_kw, gender) in GRANDPARENT_SPOUSE_MAP.items():
        if keyword in gp_name:
            counterpart_name = gp_name.replace(keyword, counterpart_kw)
            counterpart_gender = gender
            break
    
    if not counterpart_name:
        return
    
    # 检查是否已有同名人物（真实或占位）
    existing = [p for p in graph.people.values() if p.name == counterpart_name]
    if existing:
        # 已存在 → 只需建立与中间代的 parent_child 关系
        spouse = existing[0]
        existing_link = any(
            _get_rel_type_str(r) == "parent_child"
            and r.person1_id == spouse.id and r.person2_id == inter_child.id
            for r in graph.relationships.values()
        )
        if not existing_link:
            graph.add_relationship(Relationship(spouse.id, inter_child.id, RelationshipType.PARENT_CHILD, is_inferred=True))
            actions.append(f"关联已有: {counterpart_name} → {inter_child.name}")
        return
    
    # 创建配偶占位
    spouse = Person(name=counterpart_name, gender=Gender(counterpart_gender))
    spouse.is_placeholder = True
    spouse.placeholder_reason = f"{gp_name}的配偶(自动创建)"
    graph.add_person(spouse)
    newly_created_ids.add(spouse.id)
    actions.append(f"自动创建配偶(占位): {counterpart_name}")
    
    # 建立配偶→中间代的 parent_child
    graph.add_relationship(Relationship(spouse.id, inter_child.id, RelationshipType.PARENT_CHILD, is_inferred=True))
    actions.append(f"建立链路: {counterpart_name} → {inter_child.name}")
    
    # 建立与祖父母的配偶关系
    graph.add_relationship(Relationship(gp_person.id, spouse.id, RelationshipType.SPOUSE, is_inferred=True))
    actions.append(f"自动关联配偶: {gp_name} ↔ {counterpart_name}")


def _find_creation_duplicates(name: str, graph, gender: str = "unknown", exclude_id: str = None) -> list:
    """创建人物前的重复检测 — 检查是否存在相似的人物
    返回 [(person, score, reason)] 列表，按分数降序排列
    """
    results = []
    name_lower = name.lower().strip()
    name_pinyin = _get_pinyin_str(name_lower)
    name_surname, name_given = _split_chinese_name(name_lower)
    name_roles = _extract_kinship_roles(name)
    
    for p in graph.people.values():
        if exclude_id and p.id == exclude_id:
            continue
        
        p_names = [p.name]
        p_names.extend(getattr(p, 'aliases', []) or [])
        
        # 性别校验
        gender_mismatch = False
        if gender != "unknown" and p.gender and p.gender != Gender.UNKNOWN:
            p_gender_val = p.gender.value if hasattr(p.gender, 'value') else str(p.gender)
            if p_gender_val != gender:
                gender_mismatch = True

        best_score_for_person = 0
        best_reason = ""
        
        for current_name in p_names:
            p_name_lower = current_name.lower().strip()
            p_pinyin = _get_pinyin_str(p_name_lower)
            p_surname, p_given = _split_chinese_name(p_name_lower)
            
            score = 0
            reason = ""
            
            # 1. 精确匹配
            if p_name_lower == name_lower:
                score = 1.0
                reason = "姓名完全相同"
                
            # 2. 拼音完全相同
            elif p_pinyin == name_pinyin and len(name_pinyin) > 1:
                score = 0.95
                reason = f"拼音完全相同({p_pinyin})"
            
            # 3. 姓相同，名拼音相同
            elif p_surname == name_surname and _get_pinyin_str(p_given) == _get_pinyin_str(name_given) and name_given:
                score = 0.92
                reason = "同姓且名字拼音相同"
                
            # 4. 包含匹配
            elif name_lower in p_name_lower or p_name_lower in name_lower:
                if gender_mismatch:
                    score = 0.5
                else:
                    score = 0.9 if len(name_lower) >= 2 and len(p_name_lower) >= 2 else 0.7
                reason = "姓名包含匹配"
                
            # 5. 亲属角色语义匹配 (仅对主姓名)
            elif current_name == p.name and name_roles and _is_kinship_description(p.name):
                p_roles = _extract_kinship_roles(p.name)
                shared_roles = name_roles & p_roles
                if shared_roles:
                    if gender_mismatch:
                        score = 0.4
                    else:
                        has_differentiator = bool(re.search(r'[A-Za-z0-9一二三四五大六七八九十]', name))
                        existing_has_differentiator = bool(re.search(r'[A-Za-z0-9一二三四五大六七八九十]', p.name.split("的")[-1] if "的" in p.name else p.name))
                        if has_differentiator and not existing_has_differentiator:
                            score = 0.85
                        elif not has_differentiator and not existing_has_differentiator:
                            score = 0.8
                        else:
                            score = 0.6
                    reason = f"亲属角色匹配({', '.join(shared_roles)})"
            
            # 6. 编辑距离
            else:
                dist = _levenshtein(name_lower, p_name_lower)
                max_len = max(len(name_lower), len(p_name_lower))
                if max_len > 0 and dist <= max(1, int(max_len * 0.3)):
                    base_score = round(1 - dist / max_len, 2)
                    score = base_score
                    reason = f"编辑距离={dist}"

            if gender_mismatch and score > 0.4:
                score *= 0.5
                reason += "(性别不匹配)"
                
            if score > best_score_for_person:
                best_score_for_person = score
                best_reason = reason
        
        if best_score_for_person > 0.1:
            results.append((p, best_score_for_person, best_reason))
            
    return sorted(results, key=lambda x: -x[1])


def _levenshtein(s1: str, s2: str) -> int:
    """编辑距离"""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + (0 if c1 == c2 else 1)
            ))
        prev = curr
    return prev[-1]


@app.post("/api/families/{family_id}/auto-import", response_model=ApiResponse)
async def auto_import(family_id: str, request: AutoImportRequest):
    """自动导入：匹配、去重、入库，返回操作日志和需要确认的问题"""
    try:
        logger.info(f"Auto Import Started for family: {family_id}")
        graph = load_family_graph(family_id)
        parsed = request.parsed_data
        answers = request.answers or {}
        actions = []
        questions = []
        id_mapping = {}  # temp_id → real_id
        newly_created_ids = set()

        # === 0. 处理非实体类的回答 (如 parent_ambiguity) ===
        if answers:
            for q_id, answer in answers.items():
                if q_id.startswith("parent_ambiguity_"):
                    child_id = q_id.replace("parent_ambiguity_", "")
                    if answer in ("__skip__", "__cancel__"):
                        continue
                    p2_id = answer
                    p2 = graph.get_person(p2_id)
                    child = graph.get_person(child_id)
                    if p2 and child:
                        # 1. 为当前孩子添加家长
                        if not any(_get_rel_type_str(r) == "parent_child" and r.person1_id == p2_id and r.person2_id == child_id for r in graph.relationships.values()):
                            new_rel = Relationship(p2_id, child_id, RelationshipType.PARENT_CHILD, is_inferred=True)
                            new_rel.subtype = "mother" if p2.gender == Gender.FEMALE else "father"
                            graph.add_relationship(new_rel)
                            actions.append(f"手动确认家长: {p2.name} → {child.name}")
                            child.story = generate_biography_from_graph(graph, child_id)
                            
                            # 2. 联动更新兄弟姐妹（同步下游）
                            for r in list(graph.relationships.values()):
                                if _get_rel_type_str(r) == "sibling" and (r.person1_id == child_id or r.person2_id == child_id):
                                    sib_id = r.person2_id if r.person1_id == child_id else r.person1_id
                                    if not any(_get_rel_type_str(r2) == "parent_child" and r2.person1_id == p2_id and r2.person2_id == sib_id for r2 in graph.relationships.values()):
                                        new_rel_sib = Relationship(p2_id, sib_id, RelationshipType.PARENT_CHILD, is_inferred=True)
                                        new_rel_sib.subtype = new_rel.subtype
                                        graph.add_relationship(new_rel_sib)
                                        sib_person = graph.get_person(sib_id)
                                        if sib_person:
                                            sib_person.story = generate_biography_from_graph(graph, sib_id)
                                            actions.append(f"同步更新兄弟姐妹家长: {p2.name} → {sib_person.name}")
        entities = parsed.get("entities", [])
        logger.info(f"Processing {len(entities)} entities from AI parse")

        for entity in entities:
            temp_id = entity.get("temp_id", "")
            name = entity.get("name", "")
            logger.debug(f"Processing entity: {name} ({temp_id})")
            if not name:
                continue

            # 排除本批次新建的人物，避免「李梅」刚创建就被「李怀」匹配改名
            existing_people = [p for p in graph.people.values() if p.id not in newly_created_ids]

            # 亲属描述名称不走模糊匹配——直接走用户回答路径
            if _is_kinship_description(name):
                matches = []
                logger.debug(f"Entity '{name}' is kinship description, skipping fuzzy match")
            else:
                matches = _fuzzy_match(name, existing_people, gender=entity.get("gender", "unknown"))
                if matches:
                    logger.debug(f"Fuzzy matches for '{name}': {[(m[0].name, m[1]) for m in matches[:3]]}")

            # 有精确匹配（score=1.0）时直接关联，忽略其他低分候选
            exact_match = next((m for m in matches if m[1] >= 1.0), None)
            if exact_match:
                matches = [exact_match]
                logger.debug(f"Exact match found for '{name}': {exact_match[0].name}")

            if len(matches) == 1 and matches[0][1] >= 0.85:
                # 唯一高分匹配 → 自动关联，合并新信息
                person = matches[0][0]
                id_mapping[temp_id] = person.id
                updated_fields = []

                # 合并标签
                new_tags = entity.get("tags", [])
                if new_tags:
                    merged_tags = list(set(person.tags + new_tags))
                    if merged_tags != person.tags:
                        person.tags = merged_tags
                        updated_fields.append("标签")

                # 更新出生日期（如果原来没有，新信息有）
                if entity.get("birth_year") and not person.birth_date:
                    person.birth_date = entity["birth_year"]
                    updated_fields.append("出生日期")

                # 更新去世日期
                if entity.get("death_year") and not person.death_date:
                    person.death_date = entity["death_year"]
                    updated_fields.append("去世日期")

                # 更新性别（如果原来未知）
                if entity.get("gender") and entity["gender"] != "unknown" and person.gender == Gender.UNKNOWN:
                    person.gender = Gender(entity["gender"])
                    updated_fields.append("性别")

                # 更新姓名（如果新名字更正式，如从「赵大爷」→「赵大雷」）
                new_name = entity.get("name", "")
                if new_name and new_name != person.name:
                    # 禁止用亲属描述覆盖真实姓名（如「王建国」→「王建国的大伯」）
                    if _is_kinship_description(new_name):
                        pass  # 保留原名，不更新
                    # 只在新名字明显更完整时才改名（更长，且不是亲属描述）
                    # 保护已有姓名：两个不同人名绝不互相覆盖
                    elif len(new_name) > len(person.name) and not _is_kinship_description(new_name):
                        old_name = person.name
                        person.name = new_name
                        updated_fields.append(f"姓名({old_name}→{new_name})")
                    # 其他情况一律不改名——宁可保留旧名，也不误覆盖

                if updated_fields:
                    actions.append(f"更新 {person.name}: {', '.join(updated_fields)}")
                else:
                    actions.append(f"关联人物: {new_name or name} → {person.name}")

            elif len(matches) > 1:
                # 多个匹配 → 检查是否有用户回答
                q_id = f"person_match_{temp_id}"
                if q_id in answers:
                    answer = answers[q_id]
                    if answer == "__new__":
                        # 用户选择创建新人物 → 仍需检查是否与已有完全重名
                        dupes = _find_creation_duplicates(entity.get("name", ""), graph, gender=entity.get("gender", "unknown"))
                        if dupes and dupes[0][1] >= 1.0:
                            # 完全重名 → 强制关联已有
                            id_mapping[temp_id] = dupes[0][0].id
                            actions.append(f"关联人物(重名): {name} → {dupes[0][0].name}")
                        else:
                            person = _create_person_from_entity(entity)
                            graph.add_person(person)
                            id_mapping[temp_id] = person.id
                            actions.append(f"新增人物: {person.name}")
                    elif answer == "__cancel__":
                        # 用户取消 — 跳过此实体
                        actions.append(f"跳过: {name}")
                    else:
                        # 用户选择了已有人员
                        id_mapping[temp_id] = answer
                        matched_person = graph.get_person(answer)
                        if matched_person:
                            actions.append(f"关联人物: {name} → {matched_person.name}")
                else:
                    # 需要用户确认
                    questions.append({
                        "id": q_id,
                        "type": "person_match",
                        "message": f"你提到的「{name}」，是以下哪位？",
                        "entity": entity,
                        "candidates": [
                            {"id": m[0].id, "name": m[0].name, "score": m[1]}
                            for m in matches
                        ],
                    })

            else:
                # 无匹配 → 自动创建
                # 但如果名称是亲属描述（如「大伯」「王建国的大伯」），应提示用户提供真实姓名
                if _is_kinship_description(name):
                    q_id = f"person_name_{temp_id}"
                    if q_id in answers:
                        real_name = answers[q_id]
                        if real_name == "__cancel__":
                            # 用户取消 — 跳过此实体
                            actions.append(f"跳过: {name}")
                        elif real_name and real_name != "__skip__":
                            # 用户提供了真实姓名 → 先检查重复
                            entity_copy = dict(entity)
                            entity_copy["name"] = real_name
                            dupes = _find_creation_duplicates(real_name, graph, gender=entity_copy.get("gender", "unknown"))
                            if dupes and dupes[0][1] >= 0.8:
                                # 发现疑似重复 → 询问用户是否合并
                                dq_id = f"dup_check_{temp_id}"
                                if dq_id in answers:
                                    dq_answer = answers[dq_id]
                                    if dq_answer == "__new__":
                                        person = _create_person_from_entity(entity_copy)
                                        graph.add_person(person)
                                        newly_created_ids.add(person.id)
                                        id_mapping[temp_id] = person.id
                                        actions.append(f"新增人物: {person.name}（用户确认非重复）")
                                    elif dq_answer == "__cancel__":
                                        actions.append(f"跳过: {real_name}")
                                    elif dq_answer.startswith("__merge__:"):
                                        merge_target_id = dq_answer.split(":", 1)[1]
                                        id_mapping[temp_id] = merge_target_id
                                        target = graph.get_person(merge_target_id)
                                        actions.append(f"关联已有: {real_name} → {target.name}")
                                    else:
                                        actions.append(f"跳过: {real_name}")
                                else:
                                    questions.append({
                                        "id": dq_id,
                                        "type": "person_match",
                                        "message": f"「{real_name}」与已有人员相似，是否为同一人？",
                                        "entity": entity_copy,
                                        "candidates": [
                                            {"id": m[0].id, "name": m[0].name, "score": m[1], "reason": m[2]}
                                            for m in dupes[:5]
                                        ],
                                        "allow_new": True,
                                    })
                                    continue  # 等待用户回答，不继续处理此实体
                            else:
                                # 无重复 → 检查是否有匹配的占位节点可替换
                                # 检查是否有占位名称与当前实体名称匹配
                                matched_placeholder = None
                                for p in graph.people.values():
                                    if not p.is_placeholder:
                                        continue
                                    # 精确匹配：占位名称就是实体名称（如「林绿洲的妈妈」=「林绿洲的妈妈」）
                                    if p.name == name:
                                        matched_placeholder = p
                                        break
                                    # 包含匹配：占位名称包含实体的亲属角色
                                    if _is_kinship_description(name):
                                        roles = _extract_kinship_roles(name)
                                        if any(kw in p.name for kw in roles):
                                            # 检查是否关联同一个后代
                                            # 占位格式: "{child_name}的{term}"
                                            for r in graph.relationships.values():
                                                if _get_rel_type_str(r) == "parent_child" and r.person1_id == p.id:
                                                    child = graph.get_person(r.person2_id)
                                                    if child and child.name in name:
                                                        matched_placeholder = p
                                                        break
                                            if matched_placeholder:
                                                break
                                
                                if matched_placeholder:
                                    person = _create_person_from_entity(entity_copy)
                                    graph.add_person(person)
                                    replace_placeholder_with_real(graph, matched_placeholder.id, person)
                                    newly_created_ids.add(person.id)
                                    id_mapping[temp_id] = person.id
                                    actions.append(f"替换占位: {matched_placeholder.name} → {person.name}")
                                else:
                                    person = _create_person_from_entity(entity_copy)
                                    graph.add_person(person)
                                    newly_created_ids.add(person.id)
                                    id_mapping[temp_id] = person.id
                                    actions.append(f"新增人物: {person.name}")
                        else:
                            # 用户跳过 → 创建占位人物，保留关系，用户后续可改名
                            placeholder_name = name if name else f"未知{temp_id}"
                            # 检查是否已有同名人物（占位或真实）→ 复用
                            existing_same_name = [p for p in graph.people.values() if p.name == placeholder_name]
                            if existing_same_name:
                                person = existing_same_name[0]
                                id_mapping[temp_id] = person.id
                                actions.append(f"关联已有: {placeholder_name} → {person.name}")
                            else:
                                entity_copy = dict(entity)
                                entity_copy["name"] = placeholder_name
                                person = _create_person_from_entity(entity_copy)
                                person.tags = ["待确认"]
                                graph.add_person(person)
                                newly_created_ids.add(person.id)
                                id_mapping[temp_id] = person.id
                                actions.append(f"新增人物(占位): {placeholder_name} — 后续可点击改名")
                    else:
                        questions.append({
                            "id": q_id,
                            "type": "person_name",
                            "message": f"你提到的「{name}」是哪位？请提供真实姓名，或跳过自动创建占位。",
                            "entity": entity,
                            "candidates": [],
                        })
                else:
                    # 无匹配 → 必须由用户确认后才创建（防止AI误提取导致数据污染）
                    logger.info(f"No match for '{name}', triggering entity_confirm")
                    q_id = f"entity_confirm_{temp_id}"
                    if q_id in answers:
                        answer = answers[q_id]
                        if answer == "__cancel__":
                            actions.append(f"跳过: {name}")
                        elif answer == "__skip__":
                            # 创建占位人物
                            placeholder_name = name if name else f"未知{temp_id}"
                            entity_copy = dict(entity)
                            entity_copy["name"] = placeholder_name
                            person = _create_person_from_entity(entity_copy)
                            person.tags = ["待确认"]
                            graph.add_person(person)
                            newly_created_ids.add(person.id)
                            id_mapping[temp_id] = person.id
                            actions.append(f"新增人物(占位): {placeholder_name}")
                        elif answer.startswith("__create__:"):
                            # 用户确认创建，可能修改了字段
                            # 格式: __create__:name|gender|birth_date
                            parts = answer.split(":", 1)[1].split("|")
                            entity_copy = dict(entity)
                            entity_copy["name"] = parts[0] if len(parts) > 0 and parts[0] else entity["name"]
                            if len(parts) > 1 and parts[1]:
                                entity_copy["gender"] = parts[1]
                            if len(parts) > 2 and parts[2]:
                                entity_copy["birth_year"] = parts[2]
                            # 创建前检查重复
                            final_name = entity_copy["name"]
                            dupes = _find_creation_duplicates(final_name, graph, gender=entity_copy.get("gender", "unknown"))
                            if dupes and dupes[0][1] >= 0.9:
                                # 高度疑似重复 → 强制关联
                                id_mapping[temp_id] = dupes[0][0].id
                                actions.append(f"关联已有(重复检测): {final_name} → {dupes[0][0].name}")
                            else:
                                person = _create_person_from_entity(entity_copy)
                                graph.add_person(person)
                                newly_created_ids.add(person.id)
                                id_mapping[temp_id] = person.id
                                actions.append(f"新增人物: {person.name}")
                                logger.info(f"Confirmed and created person: {person.name} (ID: {person.id})")
                        else:
                            # 简单确认（兼容旧格式）→ 仍检查重复
                            final_name = entity.get("name", "")
                            dupes = _find_creation_duplicates(final_name, graph, gender=entity.get("gender", "unknown"))
                            if dupes and dupes[0][1] >= 0.9:
                                id_mapping[temp_id] = dupes[0][0].id
                                actions.append(f"关联已有(重复检测): {final_name} → {dupes[0][0].name}")
                            else:
                                person = _create_person_from_entity(entity)
                                graph.add_person(person)
                                newly_created_ids.add(person.id)
                                id_mapping[temp_id] = person.id
                                actions.append(f"新增人物: {person.name}")
                                logger.info(f"Confirmed and created person (simple): {person.name} (ID: {person.id})")
                    else:
                        questions.append({
                            "id": q_id,
                            "type": "entity_confirm",
                            "message": f"AI 提取到新人物「{name}」，请确认信息是否正确：",
                            "entity": entity,
                            "candidates": [],
                        })

        # 如果有问题需要确认，我们仍继续处理关系（只有双方都已确定的关系会被导入）
        # 但 auto_saved 标记为 False，提示前端仍有后续步骤
        has_questions = len(questions) > 0
        if has_questions:
            logger.info(f"Found {len(questions)} questions, will continue processing other data and save partially")

        # === 2. 关系处理 ===
        # 祖孙关系通过占位节点链展开为原子边(parent_child)，
        # 其他关系直接存储
        for rel in parsed.get("relationships", []):
            p1_id = id_mapping.get(rel.get("person1_temp_id", ""))
            p2_id = id_mapping.get(rel.get("person2_temp_id", ""))
            if not p1_id or not p2_id:
                continue

            # 跳过自引用关系
            if p1_id == p2_id:
                continue

            rel_type = rel.get("type", "other")
            
            p1_name = graph.get_person(p1_id).name if graph.get_person(p1_id) else "?"
            p2_name = graph.get_person(p2_id).name if graph.get_person(p2_id) else "?"

            # ── 祖孙关系 → 通过占位链展开为 parent_child 原子边 ──
            if rel_type in ("grandparent_grandchild", "grandparent"):
                gp = graph.get_person(p1_id)   # 祖父母
                gc = graph.get_person(p2_id)   # 孙辈
                if not gp or not gc:
                    continue

                # 判断支系 (优先看 subtype 或描述)
                subtype = rel.get("subtype", "")
                description = rel.get("description", "")
                is_maternal = any(kw in subtype or kw in description for kw in ["maternal", "外"])
                # fallback: 检查名字 (如「林大明的外婆」)
                if not is_maternal:
                    is_maternal = "外" in gp.name
                
                lineage = "maternal" if is_maternal else "paternal"

                # 获取或创建中间代占位（妈妈/爸爸）
                inter_gender = "female" if lineage == "maternal" else "male"
                inter_parent, inter_is_new = get_or_create_parent_placeholder(
                    graph, gc.id, lineage, inter_gender,
                    reason=f"{gc.name}的{lineage}系父母(为{gp.name}关系创建)"
                )
                if inter_parent:
                    if inter_is_new:
                        actions.append(f"自动创建中间代(占位): {inter_parent.name}")

                    # 检查祖父母→中间代的 parent_child 是否已存在
                    existing_gp_inter = any(
                        _get_rel_type_str(r) == "parent_child"
                        and r.person1_id == gp.id and r.person2_id == inter_parent.id
                        for r in graph.relationships.values()
                    )
                    if not existing_gp_inter:
                        new_rel = Relationship(gp.id, inter_parent.id, RelationshipType.PARENT_CHILD, is_inferred=False)
                        new_rel.subtype = "father" if gp.gender == Gender.MALE else "mother"
                        graph.add_relationship(new_rel)
                        actions.append(f"建立链路: {gp.name} → {inter_parent.name} → {gc.name}")

                    # 自动补全祖父母配偶（通过同一中间代）
                    _auto_create_grandparent_spouse(
                        graph, gp, inter_parent, lineage, actions, newly_created_ids
                    )
                continue

            # ── 兄弟姐妹关系 → 反向展开为共同父母 parent_child 原子边 ──
            # 确保推导引擎能通过父母链产生 downstream 推导（cousin等）
            if rel_type == "sibling":
                p1_parents = set()
                p2_parents = set()
                for r in graph.relationships.values():
                    if _get_rel_type_str(r) == "parent_child":
                        if r.person2_id == p1_id:
                            p1_parents.add(r.person1_id)
                        if r.person2_id == p2_id:
                            p2_parents.add(r.person1_id)
                shared_parents = p1_parents & p2_parents
                if not shared_parents:
                    # 一方有父母 → 另一方连接到同一父母
                    if p1_parents:
                        for parent_id in p1_parents:
                            existing_link = any(
                                _get_rel_type_str(r) == "parent_child"
                                and r.person1_id == parent_id and r.person2_id == p2_id
                                for r in graph.relationships.values()
                            )
                            if not existing_link:
                                graph.add_relationship(Relationship(parent_id, p2_id, RelationshipType.PARENT_CHILD, is_inferred=True))
                                pn = graph.get_person(parent_id)
                                actions.append(f"关联父母: {pn.name if pn else '?'} → {p2_name} (sibling推导)")
                    elif p2_parents:
                        for parent_id in p2_parents:
                            existing_link = any(
                                _get_rel_type_str(r) == "parent_child"
                                and r.person1_id == parent_id and r.person2_id == p1_id
                                for r in graph.relationships.values()
                            )
                            if not existing_link:
                                graph.add_relationship(Relationship(parent_id, p1_id, RelationshipType.PARENT_CHILD, is_inferred=True))
                                pn = graph.get_person(parent_id)
                                actions.append(f"关联父母: {pn.name if pn else '?'} → {p1_name} (sibling推导)")
                    else:
                        # 双方都没有父母 → 创建共享占位父母
                        placeholder_parent = Person(
                            name=f"{p1_name}的爸爸",
                            gender=Gender.MALE,
                        )
                        placeholder_parent.is_placeholder = True
                        placeholder_parent.placeholder_reason = f"sibling关系({p1_name}↔{p2_name})自动创建的共享父母"
                        graph.add_person(placeholder_parent)
                        
                        graph.add_relationship(Relationship(placeholder_parent.id, p1_id, RelationshipType.PARENT_CHILD, is_inferred=True))
                        graph.add_relationship(Relationship(placeholder_parent.id, p2_id, RelationshipType.PARENT_CHILD, is_inferred=True))
                        
                        actions.append(f"自动创建共享父母(占位): {placeholder_parent.name} → {p1_name}/{p2_name}")

            # ── 其他关系：直接存储 ──
            # ── 重复关系检测 ──
            is_dup = False
            for r in graph.relationships.values():
                curr_r_type = _get_rel_type_str(r)
                if curr_r_type != rel_type:
                    continue
                
                # 对等关系 (spouse, sibling): 不分先后
                if rel_type in ("spouse", "sibling", "other"):
                    if ((r.person1_id == p1_id and r.person2_id == p2_id) or
                        (r.person2_id == p1_id and r.person1_id == p2_id)):
                        is_dup = True
                        break
                # 非对等关系 (parent_child): 区分先后
                else:
                    if r.person1_id == p1_id and r.person2_id == p2_id:
                        is_dup = True
                        # 如果新关系有更具体的 subtype，更新已有的
                        if not r.subtype and rel.get("subtype"):
                            r.subtype = rel.get("subtype")
                        break
            
            if is_dup:
                logger.debug(f"Relationship already exists: {p1_name} ↔ {p2_name} ({rel_type}), skipping")
                continue

            # ── parent_child 关系：检查是否需要替换占位 ──
            # 当新父母替代已有占位父母时，自动替换
            if rel_type == "parent_child":
                parent = graph.get_person(p1_id)   # person1 是父母
                child = graph.get_person(p2_id)    # person2 是子女
                if parent and child and not parent.is_placeholder:
                    # 查找子女的同性别占位父母
                    for existing_rel in list(graph.relationships.values()):
                        if _get_rel_type_str(existing_rel) != "parent_child":
                            continue
                        if existing_rel.person2_id != child.id:
                            continue
                        existing_parent = graph.get_person(existing_rel.person1_id)
                        if not existing_parent or not existing_parent.is_placeholder:
                            continue
                        if existing_parent.gender != parent.gender:
                            continue
                        # 找到同性别占位父母 → 替换！
                        replace_placeholder_with_real(graph, existing_parent.id, parent)
                        actions.append(f"替换占位: {existing_parent.name} → {parent.name}")
                        # 更新 p1_id（关系边的person1可能已改变）
                        break

            relationship = _create_relationship_from_parsed(p1_id, p2_id, rel, graph=graph)
            graph.add_relationship(relationship)
            actions.append(f"新增关系: {p1_name} ↔ {p2_name} ({rel_type})")

        # === 2.5 一次性 BFS 扩散式关系推导 ===
        # 收集本批次所有涉及的节点，从这些节点出发做全图传播
        affected_ids = set(id_mapping.values())
        from derivation_engine import propagate_from_nodes
        derived = propagate_from_nodes(graph, affected_ids)
        for d in derived:
            actions.append(f"推导关系: {d['person_a']} ↔ {d['person_b']} ({d['type']})")

        # === 2.6 关系一致性校验（拦截矛盾/冗余关系）===
        # === 2.6 关系一致性校验 ... (保持现状) ===
        all_rel_dicts = []
        for r in graph.relationships.values():
            p1 = graph.get_person(r.person1_id)
            p2 = graph.get_person(r.person2_id)
            if p1 and p2:
                all_rel_dicts.append({
                    "id": r.id,
                    "person1_id": r.person1_id,
                    "person2_id": r.person2_id,
                    "type": r.type.value if hasattr(r.type, 'value') else str(r.type),
                    "created_at": r.created_at,
                })
        violations, removed_ids, fix_actions = validate_and_fix(all_rel_dicts)
        for rid in removed_ids:
            if rid in graph.relationships:
                del graph.relationships[rid]
        for fa in fix_actions:
            actions.append(f"校验修复: {fa}")

        # === 2.7 补充缺失父母 (智能推导与歧义询问) ===
        affected_ids = set(id_mapping.values())
        for pid in affected_ids:
            person = graph.get_person(pid)
            if not person: continue
            
            # 查找现有父母及其性别
            existing_parents = []
            for r in graph.relationships.values():
                if _get_rel_type_str(r) == "parent_child" and r.person2_id == pid:
                    p = graph.get_person(r.person1_id)
                    if p: existing_parents.append(p)
            
            # 如果只有 1 个父母，尝试补全另一半
            if len(existing_parents) == 1:
                p1 = existing_parents[0]
                # 确定我们需要找的另一半性别
                needed_gender = Gender.FEMALE if p1.gender == Gender.MALE else Gender.MALE
                
                # 寻找 P1 的所有当前配偶 (非 former)
                spouses = []
                for r in graph.relationships.values():
                    if _get_rel_type_str(r) == "spouse":
                        # 必须检查 P1 是否在关系的两端
                        if r.person1_id == p1.id:
                            other_id = r.person2_id
                        elif r.person2_id == p1.id:
                            other_id = r.person1_id
                        else:
                            continue
                        
                        sp = graph.get_person(other_id)
                        if sp and sp.gender == needed_gender and r.attributes.get("status") != "former":
                            spouses.append(sp)
                
                if len(spouses) == 1:
                    p2 = spouses[0]
                    # 检查是否已有关系
                    if not any(_get_rel_type_str(r) == "parent_child" and r.person1_id == p2.id and r.person2_id == pid for r in graph.relationships.values()):
                        new_rel = Relationship(p2.id, pid, RelationshipType.PARENT_CHILD, is_inferred=True)
                        new_rel.subtype = "mother" if p2.gender == Gender.FEMALE else "father"
                        graph.add_relationship(new_rel)
                        actions.append(f"智能关联母亲: {p2.name} (基于{p1.name}的唯一配偶)")
                        # 同步更新传记
                        person.story = generate_biography_from_graph(graph, pid)
                elif len(spouses) > 1:
                    # 存在多位配偶，触发询问
                    q_id = f"parent_ambiguity_{pid}"
                    if q_id not in answers:
                        has_questions = True
                        questions.append({
                            "questionId": q_id,
                            "questionType": "person_match",
                            "message": f"探测到 {person.name} 的父亲/母亲 {p1.name} 有多位配偶，请确认另一位家长是谁？",
                            "candidates": [{"id": s.id, "name": s.name} for s in spouses],
                            "allowNew": True
                        })

        # === 3. 事件处理 ===
        for event in parsed.get("events", []):
            ev = _create_event_from_parsed(event, id_mapping, graph)
            if ev:
                graph.add_event(ev)
                actions.append(f"新增事件: {ev.description}")

                # ── 离婚事件 → 标记为旧配偶关系 ──
                if ev.type == EventType.DIVORCE:
                    participant_ids = [p.get("person_id") for p in ev.participants if p.get("person_id")]
                    for i in range(len(participant_ids)):
                        for j in range(i + 1, len(participant_ids)):
                            a_id, b_id = participant_ids[i], participant_ids[j]
                            for r in graph.relationships.values():
                                if r.type == RelationshipType.SPOUSE and \
                                   ((r.person1_id == a_id and r.person2_id == b_id) or \
                                    (r.person1_id == b_id and r.person2_id == a_id)):
                                    r.attributes["status"] = "former"
                                    r.end_date = ev.date or datetime.now().strftime("%Y")
                                    a_p = graph.get_person(a_id)
                                    b_p = graph.get_person(b_id)
                                    actions.append(f"解除现任配偶: {a_p.name if a_p else '?'} ↔ {b_p.name if b_p else '?'} (转为前任)")

        # === 3.5 自动生成生平传记 ===
        # 为本次涉及的所有人物重新生成传记
        affected_ids = set(id_mapping.values())
        for pid in affected_ids:
            bio = generate_biography_from_graph(graph, pid)
            if bio:
                person = graph.get_person(pid)
                if person:
                    person.story = bio

        # === 4. 保存 ===
        if actions:
            save_family_graph(family_id, graph)
            logger.info(f"Auto Import: Saved {len(actions)} changes to disk")

            # === 4.5 记录编辑历史 ===
            record_action(
                family_id=family_id,
                action="auto_import",
                target_type="family",
                target_id=family_id,
                summary=f"自动导入: {len(actions)} 项变更 — {'; '.join(actions[:5])}{'...' if len(actions) > 5 else ''}",
                after={"action_count": len(actions), "actions": actions},
            )

        return ApiResponse(
            success=True,
            message="部分更新已保存" if has_questions else "族谱已更新",
            data={
                "auto_saved": not has_questions,
                "actions": actions,
                "questions": questions,
                "pending_data": parsed if has_questions else None,
                "id_mapping": id_mapping if has_questions else None,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"自动导入失败: {str(e)}")


def _create_person_from_entity(entity: dict) -> Person:
    """从 AI 实体创建 Person"""
    gender_str = entity.get("gender", "unknown")
    try:
        gender = Gender(gender_str)
    except ValueError:
        gender = Gender.UNKNOWN
    person = Person(name=entity["name"], gender=gender)
    person.birth_date = entity.get("birth_year")
    person.death_date = entity.get("death_year")
    person.tags = entity.get("tags", [])
    return person


def _create_relationship_from_parsed(p1_id: str, p2_id: str, rel: dict, graph: FamilyGraph = None) -> Relationship:
    """从 AI 关系创建 Relationship，并自动补全子类型"""
    type_str = rel.get("type", "other")
    try:
        rel_type = RelationshipType(type_str)
    except ValueError:
        rel_type = RelationshipType.OTHER
    
    relationship = Relationship(p1_id, p2_id, rel_type, is_inferred=False)
    subtype = rel.get("subtype")
    
    # 自动推导 parent_child 的 subtype (father/mother)
    if rel_type == RelationshipType.PARENT_CHILD and not subtype and graph:
        parent = graph.get_person(p1_id)
        if parent:
            if parent.gender == Gender.MALE:
                subtype = "father"
            elif parent.gender == Gender.FEMALE:
                subtype = "mother"
    
    relationship.subtype = subtype
    return relationship


def _create_event_from_parsed(event: dict, id_mapping: dict, graph: FamilyGraph):
    """从 AI 事件创建 Event"""
    type_str = event.get("type", "other")
    try:
        event_type = EventType(type_str)
    except ValueError:
        event_type = EventType.OTHER
    ev = Event(event_type, event.get("description", ""))
    ev.date = event.get("date")
    ev.date_accuracy = DateAccuracy(event.get("date_accuracy", "unknown")) if event.get("date_accuracy") else DateAccuracy.UNKNOWN
    ev.location = event.get("location")
    ev.confidence = Confidence(event.get("confidence", "medium")) if event.get("confidence") else Confidence.MEDIUM

    # 关联参与者
    for p in event.get("participants", []):
        temp_id = p.get("temp_id", "")
        real_id = id_mapping.get(temp_id)
        if not real_id:
            # 如果有参与者还未确定（比如正在等待确认中），则跳过此事件的创建
            # 等待下次确认后再全量创建
            logger.debug(f"Event '{ev.description}' skipped because participant '{temp_id}' not resolved.")
            return None
        ev.participants.append({"person_id": real_id, "role": p.get("role", "参与者")})
    return ev


# 数据导入导出API
@app.post("/api/families/{family_id}/import", response_model=ApiResponse)
async def import_data(
    family_id: str,
    data: Dict[str, Any] = ...
):
    """导入家族数据"""
    try:
        graph = FamilyGraph.from_dict(data)
        save_family_graph(family_id, graph)
        
        return ApiResponse(
            success=True,
            message="数据导入成功",
            data={
                "people_count": len(graph.people),
                "events_count": len(graph.events),
                "relationships_count": len(graph.relationships)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据导入失败: {str(e)}")

@app.get("/api/families/{family_id}/export", response_model=ApiResponse)
async def export_data(
    family_id: str
):
    """导出家族数据"""
    try:
        graph = load_family_graph(family_id)
        
        return ApiResponse(
            success=True,
            message="数据导出成功",
            data=graph.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据导出失败: {str(e)}")

# 家族管理API
@app.post("/api/families", response_model=ApiResponse)
async def create_family(name: str = Query(..., description="家族名称")):
    """创建新家族"""
    try:
        family_id = generate_family_id()
        graph = FamilyGraph()
        save_family_graph(family_id, graph)
        
        return ApiResponse(
            success=True,
            message=f"家族 '{name}' 创建成功",
            data={"family_id": family_id, "name": name}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建家族失败: {str(e)}")

@app.get("/api/families", response_model=ApiResponse)
async def list_families():
    """获取家族列表"""
    try:
        families = []
        for file in DATA_DIR.glob("family_*.json"):
            # 排除历史文件和非家族文件
            if "_edithistory" in file.stem or "_derived" in file.stem:
                continue
            family_id = file.stem
            families.append({
                "family_id": family_id,
                "file_path": str(file),
                "last_modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
        
        return ApiResponse(
            success=True,
            message=f"找到 {len(families)} 个家族",
            data=families
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取家族列表失败: {str(e)}")

# 关系推导和称谓查询API
@app.post("/api/families/{family_id}/derive", response_model=ApiResponse)
async def derive_all_relationships(family_id: str):
    """对全量关系执行推导补全"""
    try:
        graph = load_family_graph(family_id)

        persons_dict = {}
        for p in graph.people.values():
            persons_dict[p.name] = {"gender": p.gender.value if hasattr(p.gender, 'value') else str(p.gender)}
        rels_list = []
        for r in graph.relationships.values():
            p1 = graph.get_person(r.person1_id)
            p2 = graph.get_person(r.person2_id)
            if p1 and p2:
                rels_list.append({"person_a": p1.name, "person_b": p2.name, "type": r.type.value if hasattr(r.type, 'value') else str(r.type)})

        derived = derive_relationships(persons_dict, rels_list)
        TYPE_MAP = {"parent_child":"parent_child","spouse":"spouse","sibling":"sibling",
                    "grandparent":"grandparent_grandchild","grandparent_grandchild":"grandparent_grandchild"}
        name_to_id = {p.name: pid for pid, p in graph.people.items()}
        added = []

        for d in derived:
            a_id = name_to_id.get(d['person_a'])
            b_id = name_to_id.get(d['person_b'])
            if a_id and b_id:
                rel_type = TYPE_MAP.get(d['type'], "other")
                is_dup = any(
                    ((r.person1_id == a_id and r.person2_id == b_id) or
                     (r.person1_id == b_id and r.person2_id == a_id))
                    and (r.type.value if hasattr(r.type, 'value') else str(r.type)) == rel_type
                    for r in graph.relationships.values()
                )
                if not is_dup:
                    try:
                        rt = RelationshipType(rel_type)
                    except ValueError:
                        rt = RelationshipType.OTHER
                    relationship = Relationship(a_id, b_id, rt)
                    graph.add_relationship(relationship)
                    added.append("%s ↔ %s (%s)" % (d['person_a'], d['person_b'], rel_type))

        save_family_graph(family_id, graph)

        return ApiResponse(
            success=True,
            message=f"推导完成，新增 {len(added)} 条关系",
            data={"derived_relationships": added, "total_relationships": len(graph.relationships)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推导失败: {str(e)}")


@app.get("/api/families/{family_id}/resolve/{person_a_id}/{person_b_id}", response_model=ApiResponse)
async def resolve_kinship(family_id: str, person_a_id: str, person_b_id: str):
    """查询 A 对 B 的称谓（使用关系推导引擎）"""
    try:
        graph = load_family_graph(family_id)
        from relationship_engine import KinshipEngine

        p_a = graph.get_person(person_a_id)
        p_b = graph.get_person(person_b_id)
        if not p_a or not p_b:
            raise HTTPException(status_code=404, detail="人物未找到")

        # 构建 KinshipEngine
        engine = KinshipEngine()
        for p in graph.people.values():
            g = p.gender.value if hasattr(p.gender, 'value') else str(p.gender)
            engine.add_person(p.name, g)
        for r in graph.relationships.values():
            p1 = graph.get_person(r.person1_id)
            p2 = graph.get_person(r.person2_id)
            if p1 and p2:
                rt = r.type.value if hasattr(r.type, 'value') else str(r.type)
                g2 = p2.gender.value if hasattr(p2.gender, 'value') else str(p2.gender)
                if rt == "parent_child":
                    # p1 是父/母，p2 是子/女 → p2 到 p1 是 ascend
                    engine.add_link(p2.name, p1.name, "ascend", g2)
                elif rt == "spouse":
                    engine.add_link(p1.name, p2.name, "spouse", g2)
                elif rt == "sibling":
                    engine.add_link(p1.name, p2.name, "sibling", g2)
                elif rt == "grandparent_grandchild":
                    engine.add_link(p2.name, p1.name, "ascend", g2)
                else:
                    engine.add_link(p1.name, p2.name, "relative", g2)

        result = engine.resolve(p_a.name, p_b.name)

        return ApiResponse(
            success=True,
            message=f"{p_a.name} 对 {p_b.name} 的称谓: {result['label']}",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"称谓查询失败: {str(e)}")


class MergeRequest(BaseModel):
    primary_id: str = Field(..., description="保留的人物ID")
    secondary_id: str = Field(..., description="被合并的人物ID（将被删除）")


@app.get("/api/families/{family_id}/history", response_model=ApiResponse)
async def get_edit_history(
    family_id: str,
    person_id: Optional[str] = Query(None, description="按人物ID筛选"),
    limit: int = Query(50, description="返回条数上限"),
):
    """获取编辑历史"""
    try:
        if person_id:
            records = get_person_history(family_id, person_id)
        else:
            records = get_recent_history(family_id, limit)

        return ApiResponse(
            success=True,
            message=f"找到 {len(records)} 条历史记录",
            data=records,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


class MergePreviewRequest(BaseModel):
    primary_id: str = Field(..., description="候选保留人物ID")
    secondary_id: str = Field(..., description="候选被合并人物ID")


@app.post("/api/families/{family_id}/merge-preview", response_model=ApiResponse)
async def merge_preview(family_id: str, request: MergePreviewRequest):
    """预览合并结果：返回两人详细对比信息，供前端确认弹窗使用"""
    try:
        graph = load_family_graph(family_id)
        primary = graph.get_person(request.primary_id)
        secondary = graph.get_person(request.secondary_id)

        if not primary or not secondary:
            raise HTTPException(status_code=404, detail="人物不存在")
        if primary.id == secondary.id:
            raise HTTPException(status_code=400, detail="不能合并同一个人")

        def _person_summary(person):
            rels = graph.get_person_relationships(person.id)
            events = graph.get_person_events(person.id)
            return {
                "person": person.to_dict(),
                "relationship_count": len(rels),
                "event_count": len(events),
                "relationships": [
                    {
                        "id": r.id,
                        "type": r.type.value if hasattr(r.type, 'value') else str(r.type),
                        "other_person_id": r.person2_id if r.person1_id == person.id else r.person1_id,
                        "other_person_name": (graph.get_person(r.person2_id).name if r.person1_id == person.id
                                              else graph.get_person(r.person1_id).name if graph.get_person(r.person1_id) else "?"),
                    }
                    for r in rels
                ],
            }

        primary_summary = _person_summary(primary)
        secondary_summary = _person_summary(secondary)

        # 检测合并后会产生的重叠关系
        primary_rel_keys = set()
        for r in graph.get_person_relationships(primary.id):
            other_id = r.person2_id if r.person1_id == primary.id else r.person1_id
            rt = r.type.value if hasattr(r.type, 'value') else str(r.type)
            primary_rel_keys.add((other_id, rt))

        overlap_rels = []
        for r in graph.get_person_relationships(secondary.id):
            other_id = r.person2_id if r.person1_id == secondary.id else r.person1_id
            rt = r.type.value if hasattr(r.type, 'value') else str(r.type)
            if (other_id, rt) in primary_rel_keys:
                other = graph.get_person(other_id)
                overlap_rels.append(f"{other.name if other else '?'} ({rt})")

        return ApiResponse(
            success=True,
            message="合并预览",
            data={
                "primary": primary_summary,
                "secondary": secondary_summary,
                "overlap_relationships": overlap_rels,
                "will_delete_secondary": True,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合并预览失败: {str(e)}")


@app.post("/api/families/{family_id}/merge", response_model=ApiResponse)
async def merge_persons(family_id: str, request: MergeRequest):
    """合并两个人物：将 secondary 合并到 primary，删除 secondary"""
    try:
        graph = load_family_graph(family_id)
        primary = graph.get_person(request.primary_id)
        secondary = graph.get_person(request.secondary_id)

        if not primary:
            raise HTTPException(status_code=404, detail=f"人物 {request.primary_id} 不存在")
        if not secondary:
            raise HTTPException(status_code=404, detail=f"人物 {request.secondary_id} 不存在")
        if primary.id == secondary.id:
            raise HTTPException(status_code=400, detail="不能合并同一个人")

        people_before_count = len(graph.people)
        actions = []

        # 1. 补充 primary 缺失的字段
        if not primary.birth_date and secondary.birth_date:
            primary.birth_date = secondary.birth_date
            actions.append(f"继承出生日期: {secondary.birth_date}")
        if not primary.death_date and secondary.death_date:
            primary.death_date = secondary.death_date
            actions.append(f"继承去世日期: {secondary.death_date}")
        if not primary.birth_place and secondary.birth_place:
            primary.birth_place = secondary.birth_place
        if not primary.current_residence and secondary.current_residence:
            primary.current_residence = secondary.current_residence
        if not primary.notes and secondary.notes:
            primary.notes = secondary.notes
        if not primary.story and secondary.story:
            primary.story = secondary.story
        if primary.gender == Gender.UNKNOWN and secondary.gender != Gender.UNKNOWN:
            primary.gender = secondary.gender

        # 合并标签
        merged_tags = list(set(primary.tags + secondary.tags))
        if merged_tags != primary.tags:
            primary.tags = merged_tags

        primary.updated_at = datetime.now().isoformat()

        # 2. 迁移关系：所有指向 secondary 的关系改为指向 primary
        rels_to_remove = []
        for rel in graph.relationships.values():
            if rel.person1_id == secondary.id and rel.person2_id == primary.id:
                # 自反关系（secondary→primary 指向 primary→secondary），直接删除
                rels_to_remove.append(rel.id)
            elif rel.person2_id == secondary.id and rel.person1_id == primary.id:
                rels_to_remove.append(rel.id)
            elif rel.person1_id == secondary.id:
                rel.person1_id = primary.id
            elif rel.person2_id == secondary.id:
                rel.person2_id = primary.id

        for rid in rels_to_remove:
            del graph.relationships[rid]

        # 去重：如果迁移后出现完全相同的关系，删除重复项
        seen_rels = set()
        dup_rel_ids = []
        for rel in graph.relationships.values():
            rt = rel.type.value if hasattr(rel.type, 'value') else str(rel.type)
            key = (rel.person1_id, rel.person2_id, rt)
            rev_key = (rel.person2_id, rel.person1_id, rt)
            if key in seen_rels or rev_key in seen_rels:
                dup_rel_ids.append(rel.id)
            seen_rels.add(key)
        for rid in dup_rel_ids:
            del graph.relationships[rid]

        # 3. 迁移事件参与者
        for event in graph.events.values():
            for p in event.participants:
                if p.get("person_id") == secondary.id:
                    p["person_id"] = primary.id

        # 4. 删除 secondary（安全检查：只删这一个人）
        assert secondary.id in graph.people, f"安全检查失败: {secondary.id} 不在人物列表中"
        del graph.people[secondary.id]
        # 验证没有误删其他人
        assert len(graph.people) == people_before_count - 1, \
            f"合并异常: 预期 {people_before_count - 1} 人，实际 {len(graph.people)} 人"

        # 5. 合并后重新执行关系推导（传递性：兄弟关系、夫妻→父母等）
        persons_dict = {}
        for p in graph.people.values():
            persons_dict[p.name] = {"gender": p.gender.value if hasattr(p.gender, 'value') else str(p.gender)}
        rels_list = []
        for r in graph.relationships.values():
            p1 = graph.get_person(r.person1_id)
            p2 = graph.get_person(r.person2_id)
            if p1 and p2:
                rels_list.append({"person_a": p1.name, "person_b": p2.name, "type": r.type.value if hasattr(r.type, 'value') else str(r.type)})

        derived = derive_relationships(persons_dict, rels_list)
        name_to_id = {p.name: pid for pid, p in graph.people.items()}
        TYPE_MAP = {"parent_child":"parent_child","spouse":"spouse","sibling":"sibling",
                    "grandparent":"grandparent_grandchild","grandparent_grandchild":"grandparent_grandchild"}

        for d in derived:
            a_id = name_to_id.get(d['person_a'])
            b_id = name_to_id.get(d['person_b'])
            if a_id and b_id:
                rel_type = TYPE_MAP.get(d['type'], "other")
                is_dup = any(
                    ((r.person1_id == a_id and r.person2_id == b_id) or
                     (r.person1_id == b_id and r.person2_id == a_id))
                    and (r.type.value if hasattr(r.type, 'value') else str(r.type)) == rel_type
                    for r in graph.relationships.values()
                )
                if not is_dup:
                    try:
                        rt = RelationshipType(rel_type)
                    except ValueError:
                        rt = RelationshipType.OTHER
                    relationship = Relationship(a_id, b_id, rt)
                    graph.add_relationship(relationship)
                    actions.append(f"推导关系: {d['person_a']} ↔ {d['person_b']} ({rel_type})")

        # 6. 关系一致性校验（拦截矛盾/冗余关系）
        all_rel_dicts = []
        for r in graph.relationships.values():
            p1 = graph.get_person(r.person1_id)
            p2 = graph.get_person(r.person2_id)
            if p1 and p2:
                all_rel_dicts.append({
                    "id": r.id,
                    "person1_id": r.person1_id,
                    "person2_id": r.person2_id,
                    "type": r.type.value if hasattr(r.type, 'value') else str(r.type),
                    "created_at": r.created_at,
                })
        violations, removed_ids, fix_actions = validate_and_fix(all_rel_dicts)
        for rid in removed_ids:
            if rid in graph.relationships:
                del graph.relationships[rid]
        for fa in fix_actions:
            actions.append(f"校验修复: {fa}")

        # 7. 保存
        save_family_graph(family_id, graph)

        # 8. 记录编辑历史
        record_action(
            family_id=family_id,
            action="merge",
            target_type="person",
            target_id=primary.id,
            target_name=primary.name,
            before={"primary": primary.name, "secondary": secondary.name},
            after={"merged_name": primary.name, "actions": actions},
            summary=f"合并: 「{secondary.name}」→「{primary.name}」（{len(actions)} 项变更）",
        )

        actions.insert(0, f"合并完成: 「{secondary.name}」→「{primary.name}」")
        return ApiResponse(
            success=True,
            message=f"已将「{secondary.name}」合并到「{primary.name}」",
            data={"actions": actions, "primary": primary.to_dict()}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合并失败: {str(e)}")


# 启动应用
if __name__ == "__main__":
    print("启动家族编年史API服务器...")
    print("API文档: http://localhost:8000/api/docs")
    print("ReDoc文档: http://localhost:8000/api/redoc")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )