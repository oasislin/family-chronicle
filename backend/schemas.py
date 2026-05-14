from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

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

class ChatExtractRequest(BaseModel):
    text: str = Field(..., description="用户输入的自然语言")
    family_id: str = Field(..., description="家族ID")

class ChatCommitRequest(BaseModel):
    family_id: str = Field(..., description="家族ID")
    confirmed_entities: List[Dict[str, Any]]
    confirmed_relationships: List[Dict[str, Any]]
    confirmed_events: List[Dict[str, Any]]
    resolutions: Optional[Dict[str, str]] = Field({}, description="针对推导歧义的路径解析方案 (key -> target_person_id)")
    extra_actions: Optional[List[Dict[str, Any]]] = Field([], description="针对歧义建议的直接执行动作 (如 ADD_EDGE)")

class TaskResolutionRequest(BaseModel):
    family_id: str = Field(..., description="家族ID")
    task_id: str = Field(..., description="任务ID")
    action: str = Field(..., description="执行的动作")
    payload: Optional[Dict[str, Any]] = Field({}, description="动作所需的数据载荷")
    target_id: Optional[str] = Field(None, description="目标实体ID（可选）")

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
