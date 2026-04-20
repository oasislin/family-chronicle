# 家族编年史（Family Chronicle） — 项目设计方案

> 版本：v1.0 · 2026-04-20

---

## 1. 项目概述

### 1.1 愿景

「家族编年史」是一个智能族谱系统，让用户通过**自然语言输入**来构建和维护家族图谱。

**设计哲学：用户只做一件半事。**
- **一件事**：输入文字，告诉系统家族故事。
- **半件事**：系统不确定时，回答一个具体的提问。

系统是一个**倾听者和整理者**——用户说完，家谱就更新了。

### 1.2 核心特性

| 特性 | 说明 |
|------|------|
| 自然语言输入 | 用白话描述家族信息，AI 自动解析为结构化数据 |
| 智能图谱 | 实时可视化家族关系网络，支持拖拽布局 |
| 自动关系推导 | 从已知关系推导缺失关系（夫妻→父母、同父母→兄弟） |
| 人物合并 | "A是B" 即可合并两人，AI 语义理解各种表达方式 |
| 冲突检测 | 自动检测矛盾/冗余关系，写入前拦截 |
| 生平生成 | 从关系和事件自动生成人物传记 |
| 编辑历史 | 记录每次增删改操作，可追溯 |

---

## 2. 技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (React + TypeScript)              │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ InputBar  │  │ FamilyGraph  │  │  PersonDetail    │  │
│  │ (输入条)  │  │ (图谱可视化)  │  │  (人物详情面板)   │  │
│  └────┬─────┘  └──────┬───────┘  └────────┬─────────┘  │
│       │               │                    │             │
│  ┌────┴───────────────┴────────────────────┴─────────┐  │
│  │              App.tsx (状态中枢)                     │  │
│  │  MessageFeed · MergeConfirmDialog · QuestionCard  │  │
│  └────────────────────┬──────────────────────────────┘  │
│                       │ API 调用                         │
└───────────────────────┼─────────────────────────────────┘
                        │ HTTP/JSON
┌───────────────────────┼─────────────────────────────────┐
│                  后端 (FastAPI + Python)                  │
│  ┌────────────────────┴──────────────────────────────┐  │
│  │              main.py (API 路由层)                   │  │
│  └──┬──────┬──────┬──────┬──────┬──────┬──────┬─────┘  │
│     │      │      │      │      │      │      │         │
│  ┌──┴──┐┌──┴──┐┌──┴──┐┌──┴──┐┌──┴──┐┌──┴──┐┌──┴──┐    │
│  │ AI  ││自动 ││合并 ││推导 ││校验 ││生平 ││历史 │    │
│  │解析 ││导入 ││引擎 ││引擎 ││器   ││引擎 ││记录 │    │
│  └──┬──┘└──┬──┘└──┬──┘└──┬──┘└──┬──┘└──┬──┘└──┬──┘    │
│     │      │      │      │      │      │      │         │
│  ┌──┴──────┴──────┴──────┴──────┴──────┴──────┴─────┐  │
│  │           JSON 文件存储 (data/*.json)              │  │
│  │  {family_id}.json · {family_id}_edithistory.json  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端框架 | React 18 + TypeScript | 组件化 UI |
| 图谱可视化 | React Flow | 节点-边图谱渲染，支持拖拽/缩放 |
| 前端样式 | Tailwind CSS | 原子化 CSS，快速迭代 |
| 后端框架 | FastAPI | 异步 Python Web 框架 |
| 数据存储 | JSON 文件 | 无数据库依赖，零配置 |
| AI 服务 | 华为 DeepSeek 3.2 | OpenAI 兼容 API |
| 人物头像 | DiceBear (avataaars) | 免费 SVG 头像生成 |

### 2.3 数据存储

所有数据以 JSON 文件存储在 `backend/data/` 目录下：

| 文件 | 说明 |
|------|------|
| `{family_id}.json` | 家族主数据（人物、关系、事件） |
| `{family_id}_edithistory.json` | 编辑历史记录（最多 1000 条） |

---

## 3. 数据模型

### 3.1 Person（人物）

```python
class Person:
    id: str              # person_{uuid8}
    name: str            # 姓名
    gender: Gender       # male / female / unknown
    birth_date: str      # 出生日期（可选）
    death_date: str      # 去世日期（可选）
    birth_place: str     # 出生地（可选）
    current_residence: str  # 现居地（可选）
    tags: List[str]      # 标签（如 "长子"、"村长"）
    notes: str           # 备注（可选）
    story: str           # 生平传记（自动生成）
    created_at: str      # ISO 时间戳
    updated_at: str      # ISO 时间戳
```

### 3.2 Relationship（关系）

```python
class Relationship:
    id: str              # rel_{uuid8}
    person1_id: str      # 人物1 ID
    person2_id: str      # 人物2 ID
    type: RelationshipType  # 关系类型枚举
    subtype: str         # 子类型（如 father/mother）
    start_date: str      # 关系开始日期
    end_date: str        # 关系结束日期
    attributes: dict     # 扩展属性
    event_id: str        # 关联事件 ID
    notes: str           # 备注
    created_at: str      # ISO 时间戳
```

**关系类型枚举：**

| 类型 | 说明 |
|------|------|
| `parent_child` | 亲子关系 |
| `spouse` | 配偶 |
| `sibling` | 兄弟姐妹 |
| `grandparent_grandchild` | 祖孙 |
| `aunt_uncle_niece_nephew` | 叔侄 |
| `cousin` | 表亲 |
| `adopted_parent_child` | 过继 |
| `godparent_godchild` | 干亲 |
| `in_law` | 姻亲 |
| `other` | 其他 |

### 3.3 Event（事件）

```python
class Event:
    id: str              # event_{uuid8}
    type: EventType      # 出生/死亡/结婚/离婚/过继/生病/搬家/教育/职业/认干亲/其他
    description: str     # 事件描述
    date: str            # 日期
    date_accuracy: DateAccuracy  # exact / year / approximate / unknown
    location: str        # 地点
    participants: List[Dict]  # [{"person_id": "...", "role": "..."}]
    source: str          # 信息来源
    confidence: Confidence  # high / medium / low / uncertain
    created_at: str      # ISO 时间戳
```

### 3.4 EditHistory（编辑历史）

```json
{
  "id": "hist_{uuid8}",
  "timestamp": "2026-04-20T12:00:00",
  "action": "create_person | update_person | delete_person | merge | auto_import",
  "actor": "user",
  "target_type": "person | relationship | event | family",
  "target_id": "person_xxx",
  "target_name": "张三",
  "before": null,
  "after": {"name": "张三", "gender": "male", ...},
  "summary": "新增人物: 张三"
}
```

---

## 4. 后端模块详解

### 4.1 API 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/families` | 创建家族 |
| `GET` | `/api/families` | 列出家族 |
| `GET` | `/api/families/{id}/export` | 导出家族数据 |
| `POST` | `/api/families/{id}/import` | 导入家族数据 |
| `POST` | `/api/families/{id}/people` | 创建人物 |
| `GET` | `/api/families/{id}/people` | 列出人物（支持搜索/筛选） |
| `GET` | `/api/families/{id}/people/{pid}` | 人物详情（含关系/事件） |
| `PUT` | `/api/families/{id}/people/{pid}` | 更新人物 |
| `DELETE` | `/api/families/{id}/people/{pid}` | 删除人物 |
| `POST` | `/api/families/{id}/people/{pid}/biography` | 重新生成传记 |
| `POST` | `/api/families/{id}/biography/batch` | 批量生成传记 |
| `POST` | `/api/families/{id}/relationships` | 创建关系 |
| `GET` | `/api/families/{id}/relationships` | 列出关系 |
| `DELETE` | `/api/families/{id}/relationships/{rid}` | 删除关系 |
| `POST` | `/api/families/{id}/events` | 创建事件 |
| `GET` | `/api/families/{id}/events` | 列出事件 |
| `POST` | `/api/ai/parse` | AI 解析自然语言 |
| `POST` | `/api/ai/detect-intent` | AI 意图检测（合并意图） |
| `POST` | `/api/families/{id}/auto-import` | **核心**：自动导入 |
| `POST` | `/api/families/{id}/merge-preview` | 合并预览 |
| `POST` | `/api/families/{id}/merge` | 执行合并 |
| `POST` | `/api/families/{id}/derive` | 全量关系推导 |
| `POST` | `/api/conflict/check` | 冲突检测 |
| `GET` | `/api/families/{id}/history` | 编辑历史查询 |
| `GET` | `/api/families/{id}/resolve/{a}/{b}` | 称谓查询 |

### 4.2 核心流程：auto-import

`POST /api/families/{id}/auto-import` 是系统的核心端点，实现"一件半事"理念。

**输入：** AI 解析结果 + 可选的用户回答

**处理流程：**

```
1. 人物处理（逐个实体）
   ├─ 模糊匹配已有姓名（精确/包含/编辑距离）
   ├─ 唯一高分匹配 (≥0.85) → 自动关联 + 合并新信息
   ├─ 多个匹配 → 生成提问 或 接收用户回答
   ├─ 无匹配 + 亲属描述 → 请求真实姓名 或 创建占位
   └─ 无匹配 + 普通姓名 → 直接创建

2. 关系处理
   ├─ Temp ID → Real ID 映射
   ├─ 双向去重检查
   └─ 创建关系

2.5 关系推导补全
   ├─ 夫妻 + 父子 → 母子/父子
   ├─ 同父母 → 兄弟姐妹
   └─ 父子链 → 祖孙

2.6 关系一致性校验
   ├─ 自引用检测
   ├─ 矛盾关系对检测
   └─ 冗余祖孙关系清理

3. 事件处理
   └─ 创建事件 + 关联参与者

3.5 自动生成传记
   └─ 为涉及人物重新生成生平

4. 保存 + 编辑历史记录
```

### 4.3 关系推导引擎 (derivation_engine.py)

从已知关系推导缺失关系：

| 规则 | 输入 | 输出 |
|------|------|------|
| 夫妻推导 | A♂ 是 C 的父 + A 与 B 是夫妻 | B♀ 是 C 的母 |
| 兄弟推导 | A 和 B 有共同父母 | A ↔ B 兄弟姐妹 |
| 祖孙推导 | A 是 B 的父 + B 是 C 的父 | A 是 C 的祖父 |

### 4.4 关系校验器 (relationship_validator.py)

在关系写入前检查一致性：

| 规则 | 级别 | 处理 |
|------|------|------|
| 自引用 (A↔A) | error | 自动移除 |
| parent_child + sibling | error | 保留最早，移除矛盾 |
| parent_child + spouse | error | 保留最早，移除矛盾 |
| 冗余祖孙 (已有亲子链) | warning | 自动移除冗余 |
| 重复关系 | warning | 自动去重 |

### 4.5 生平生成引擎 (biography_engine.py)

从结构化数据自动生成传记，纯模板规则，零 LLM 消耗。

**生成内容：**
- 基本信息（姓名、性别、出生地）
- 家庭关系（父母、配偶、子女、兄弟姐妹）
- 人生事件（按时间排序）
- 社会关系（叔侄、表亲、干亲等）

**交叉引用：** 传记中使用 `{{person:ID}}` 占位符，前端渲染时解析为当前姓名。

### 4.6 编辑历史模块 (history.py)

| 功能 | 说明 |
|------|------|
| `record_action()` | 记录操作（含 before/after 快照） |
| `get_person_history()` | 按人物筛选历史 |
| `get_recent_history()` | 最近 N 条历史 |

**接入点：** create/update/delete person、auto-import、merge

---

## 5. 前端组件架构

### 5.1 组件树

```
App.tsx (状态中枢)
├── Header (顶部导航 + 搜索)
├── FamilyGraphView (React Flow 图谱)
│   └── PersonNode (自定义节点)
│       ├── DiceBear 头像
│       └── 毛玻璃名字标签
├── MessageFeed (右侧消息流)
│   ├── ParsingCard (解析中)
│   ├── SuccessCard (成功，5秒自动收起)
│   ├── QuestionCard (歧义确认)
│   │   ├── 场景1: 人物匹配 (候选人列表 + 手动输入 + 取消)
│   │   ├── 场景2: 逻辑矛盾 (以新/旧为准 + 手动输入 + 取消)
│   │   ├── 场景3: AI低置信度 (确认/跳过 + 手动编辑 + 取消)
│   │   └── 场景4: 关系方向 (选项按钮 + 取消)
│   ├── ErrorCard (错误 + 重试)
│   └── SuggestionCard (追问建议)
├── InputBar (底部固定输入条)
│   ├── Textarea (自动调整高度)
│   └── 发送按钮 (⌘+Enter 快捷键)
├── MergeConfirmDialog (合并确认弹窗)
│   ├── 双人物对比卡片
│   ├── 方向选择 (点击切换)
│   ├── 高级选项 (自定义名称)
│   └── 关系/事件数量预览
└── PersonDetail (底部滑出面板)
    ├── 基本信息 Tab (查看/编辑)
    ├── 时间线 Tab (事件 + 编辑历史)
    ├── 关系网络 Tab (关系列表 + 删除)
    ├── 生平故事 Tab (自动生成 + 手动编辑)
    └── 添加 Tab (添加关系/事件)
```

### 5.2 核心交互流程

```
用户输入文字
    │
    ▼
handleSend()
    │
    ├─► intentApi.detect() — AI判断是否合并意图
    │   │
    │   ├─ 是 + 两人在库 → 弹出 MergeConfirmDialog
    │   │   └─ 用户确认 → mergeApi.run() → 刷新图谱
    │   │
    │   └─ 否 → 进入正常解析流程
    │
    ├─► aiApi.parse() — AI 解析自然语言
    │   └─ 返回 { entities, events, relationships, metadata }
    │
    └─► autoImportApi.run() — 自动导入
        │
        ├─ auto_saved=true → 显示 SuccessCard
        │   └─ 刷新图谱
        │
        └─ auto_saved=false → 显示 QuestionCard(s)
            └─ 用户回答 → handleAnswer() → 重新 auto-import
```

### 5.3 图谱节点样式 (PersonNode)

**性别差异化视觉：**

| 属性 | 男性 ♂ | 女性 ♀ | 未知 |
|------|--------|--------|------|
| 头像边框 | 3px 实线蓝色 | 3px 虚线粉色 | 2.5px 实线灰色 |
| 头像辉光 | 蓝色辉光 | 粉色辉光 | 灰色辉光 |
| 名字前缀 | ♂ | ♀ | 无 |
| 标签底色 | 蓝调半透明 | 粉调半透明 | 灰调半透明 |
| DiceBear 风格 | avataaars (男性参数) | avataaars (女性参数) | avataaars (中性) |

**状态指示：**
- 已故人物：灰度 + 半透明 + ✝ 前缀 + 删除线
- 待确认人物：黄色标签
- 选中状态：黄色光圈 + 放大 110%

---

## 6. AI 集成

### 6.1 AI 服务配置

| 配置项 | 当前值 | 说明 |
|--------|--------|------|
| `AI_PROVIDER` | `deepseek` | AI 服务提供商 |
| `DEEPSEEK_API_KEY` | 华为 ModelArts 密钥 | API 认证 |
| `DEEPSEEK_BASE_URL` | `https://api.modelarts-maas.com/openai/v1` | 兼容 OpenAI 格式 |

### 6.2 AI 使用场景

| 场景 | 端点 | 消耗 |
|------|------|------|
| 自然语言解析 | `/api/ai/parse` | ~2000 tokens |
| 意图检测 | `/api/ai/detect-intent` | ~200 tokens |

**解析输出格式：**

```json
{
  "entities": [
    {
      "type": "person",
      "name": "王建国",
      "temp_id": "temp_person_001",
      "gender": "male",
      "birth_year": "1980",
      "tags": ["老二"],
      "confidence": "high"
    }
  ],
  "relationships": [
    {
      "person1_temp_id": "temp_person_002",
      "person2_temp_id": "temp_person_001",
      "type": "parent_child",
      "subtype": "father"
    }
  ],
  "events": [
    {
      "type": "marriage",
      "description": "王建国与李梅结婚",
      "date": "2005",
      "participants": [
        {"temp_id": "temp_person_001", "role": "新郎"},
        {"temp_id": "temp_person_003", "role": "新娘"}
      ]
    }
  ],
  "metadata": {
    "parsing_confidence": 0.9,
    "ambiguous_references": [],
    "suggested_questions": ["建国和李梅结婚具体是哪一年？"]
  }
}
```

### 6.3 意图检测

当用户输入包含两个人名时，AI 判断是否为合并意图：

```
输入: "小丫头的妈妈叫冯牡丹"
AI 输出: {"names": ["小丫头的妈妈", "冯牡丹"]}
后端验证: 两人均在库中 → is_merge = true
```

支持的表达方式：`A是B`、`A就是B`、`A叫B`、`A的真名是B`、`A又名B` 等。

---

## 7. 数据一致性保障

### 7.1 写入前校验流程

```
auto-import / merge
    │
    ├─ 1. 关系推导 (derive_relationships)
    │
    ├─ 2. 一致性校验 (validate_and_fix)
    │   ├─ 自引用 → 移除
    │   ├─ 矛盾关系对 → 保留最早
    │   └─ 冗余祖孙 → 移除冗余
    │
    └─ 3. 保存 + 记录历史
```

### 7.2 合并安全机制

- **断言检查：** 合并前后人物数量验证（确保只删 1 人）
- **关系迁移：** 所有指向被合并者的关系自动转移
- **自反关系清理：** primary ↔ secondary 的自反关系直接删除
- **重复关系去重：** 迁移后出现的完全相同关系自动去重
- **事件参与者迁移：** 事件中的参与者 ID 自动更新
- **合并后推导：** 合并后重新执行关系推导，确保传递性关系正确

---

## 8. 部署与运行

### 8.1 后端启动

```bash
cd backend
pip install -r requirements.txt
python main.py
# → http://localhost:8000
# → API 文档: http://localhost:8000/api/docs
```

### 8.2 前端启动

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 8.3 环境变量

```bash
# backend/.env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-key
DEEPSEEK_BASE_URL=https://api.modelarts-maas.com/openai/v1
```

### 8.4 前端代理

前端 `vite.config.ts` 配置了 API 代理：

```typescript
proxy: {
  '/api': { target: 'http://localhost:8000', changeOrigin: true }
}
```

---

## 9. 文件清单

### 9.1 后端文件

| 文件 | 说明 |
|------|------|
| `main.py` | FastAPI 主应用（~1900 行） |
| `models.py` | 数据模型定义 |
| `config.py` | 配置管理 |
| `prompt_engineering.py` | AI 提示词工程 |
| `derivation_engine.py` | 关系推导引擎 |
| `biography_engine.py` | 生平生成引擎 |
| `relationship_validator.py` | 关系一致性校验器 |
| `conflict_detector.py` | 冲突检测引擎 |
| `relationship_engine.py` | 称谓查询引擎 |
| `history.py` | 编辑历史模块 |

### 9.2 前端文件

| 文件 | 说明 |
|------|------|
| `src/App.tsx` | 状态中枢、交互逻辑 |
| `src/components/FamilyGraph.tsx` | React Flow 图谱 + PersonNode |
| `src/components/InputBar.tsx` | 底部输入条 |
| `src/components/MessageFeed.tsx` | 消息流（5 种卡片） |
| `src/components/MergeConfirmDialog.tsx` | 合并确认弹窗 |
| `src/components/PersonDetail.tsx` | 人物详情面板（5 Tab） |
| `src/components/PersonPicker.tsx` | 人物选择器 |
| `src/components/EventForm.tsx` | 事件表单 |
| `src/components/StoryEditor.tsx` | 传记编辑器 |
| `src/services/api.ts` | API 客户端 |
| `src/types.ts` | TypeScript 类型定义 |

---

## 10. 已知限制与未来方向

### 10.1 当前限制

| 限制 | 说明 |
|------|------|
| 单用户 | 无认证机制，所有操作共享同一数据 |
| 无数据库 | JSON 文件存储，不适合大规模数据 |
| 无撤销 | 历史记录已保存，但未实现撤销功能 |
| 无导入导出 | 数据格式未标准化，暂不支持 GEDCOM |
| AI 依赖 | 解析质量取决于 AI 服务可用性 |

### 10.2 未来方向

| 方向 | 说明 |
|------|------|
| 语音输入 | Web Speech API 录音 → 转文字 → 自动填入 |
| 多用户 | 添加认证机制，支持多家族管理 |
| 协作编辑 | 多人同时编辑同一族谱 |
| GEDCOM 支持 | 导入导出标准族谱格式 |
| 图片 OCR | 从老照片/家谱图中提取信息 |
| 撤销/重做 | 基于编辑历史实现操作回滚 |
| 时间线可视化 | 按时间轴展示家族大事记 |

---

## 附录 A：关键设计决策

### A.1 AI 优于正则

正则表达式无法覆盖中文的各种表达方式（"A叫B"、"A就是B"、"A的真名叫B"等）。采用 AI 语义理解，准确率显著提升。

### A.2 JSON 文件存储

选择 JSON 文件而非数据库的原因：
- 零配置，无需安装数据库
- 数据可读，方便调试和备份
- 适合单用户/小规模场景
- 未来可平滑迁移到 SQLite/PostgreSQL

### A.3 "一件半事" 交互理念

传统族谱软件需要用户手动填写表单、选择关系类型、指定方向——操作繁琐。「家族编年史」将复杂度交给 AI，用户只需叙述故事，系统自动处理一切。

### A.4 关系推导的必要性

用户通常不会一次性说清所有关系。系统通过推导引擎自动补全隐含关系：
- "张三是李四的爸爸" → 自动推导李四的母亲（如果知道张三的配偶）
- "王大是王二的爸爸，王二是王三的爸爸" → 自动推导王大是王三的爷爷

---

*文档由 AI 辅助生成，基于实际代码实现。*
