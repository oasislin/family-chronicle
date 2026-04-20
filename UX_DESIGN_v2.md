# 家族编年史 — 操作逻辑规范 v2

## 核心设计原则

> **默认信任 AI，用户只需否决错误项。**
> 不是「用户逐条确认入库」，而是「AI 预处理一切，用户只需取消勾选错的」。

---

## 完整工作流

### 阶段1：AI 解析

用户在左侧输入文本，点击 AI 解析。

### 阶段2：智能预处理（系统自动完成，无需用户操作）

AI 返回 entities / events / relationships 后，系统自动执行：

#### 2a. 人物匹配
```
对每个识别到的人物 entity：
  ├─ 在现有数据库中按姓名模糊匹配（编辑距离 ≤ 1）
  │   ├─ 找到匹配 → 标记为「关联到: 王建国」，不创建新记录
  │   └─ 未找到   → 标记为「新建」
  └─ 所有状态预填好，用户不需要手动选择
```

#### 2b. 关系去重
```
对每个识别到的关系 relationship：
  ├─ 用匹配后的人物真实 ID 替换 temp_id
  ├─ 检查数据库中是否已存在相同关系（A→B 同类型）
  │   ├─ 已存在 → 标记为「重复，跳过」
  │   └─ 不存在 → 标记为「待创建」
  └─ 同一组人物的同类型关系只能有一条
```

#### 2c. 事件关联
```
对每个识别到的事件 event：
  ├─ 用匹配后的人物真实 ID 替换 temp_id 中的参与者
  ├─ 标记为「待创建」
  └─ 入库时自动建立人物-事件关联
```

### 阶段3：用户确认界面（待办校正台）

**展示一个预览清单，每项带复选框，默认全部勾选。**

```
┌─ 待办校正台 ─────────────────────────────┐
│                                          │
│  AI 解析完成，以下内容将入库：             │
│  取消勾选不需要的项目，然后点击「确认入库」│
│                                          │
│  👤 人物 (3)                              │
│  ┌──────────────────────────────────────┐│
│  │ ☑ 👨 王建国  ← 已匹配到数据库中现有记录 ││
│  │ ☑ 👩 李菊花  ← 新建人物                ││
│  │ ☐ 👤 王小明  ← 新建人物 (置信度低)     ││
│  └──────────────────────────────────────┘│
│                                          │
│  💒 事件 (2)                              │
│  ┌──────────────────────────────────────┐│
│  │ ☑ 1995 王建国与李梅结婚                ││
│  │    参与者: 王建国(新郎), 李梅(新娘)     ││
│  │ ☑ 1996 王建国认赵大爷为干爹            ││
│  │    参与者: 王建国(干儿子), 赵大爷(干爹) ││
│  └──────────────────────────────────────┘│
│                                          │
│  🔗 关系 (2)                              │
│  ┌──────────────────────────────────────┐│
│  │ ☑ 👨王大强 → 👨王建国  亲子关系        ││
│  │ ☐ 👨王建国 ↔ 👩李梅  配偶 ⚠️ 已存在    ││
│  └──────────────────────────────────────┘│
│                                          │
│  ┌──────────────────────────────────────┐│
│  │        ✅ 确认入库 (4 项)              ││
│  └──────────────────────────────────────┘│
│                                          │
│  取消勾选了 2 项，将创建 2 个人物、          │
│  2 个事件、1 条关系                        │
└──────────────────────────────────────────┘
```

### 阶段4：一键入库

用户点击「确认入库」：
1. 创建所有勾选的人物（已匹配的跳过创建，只更新标签）
2. 创建所有勾选的事件（自动关联参与者）
3. 创建所有勾选的关系（已存在的跳过）
4. 刷新图谱
5. 清空待办校正台

**整个过程只需要用户点一次按钮。** 如果 AI 解析结果全部正确，用户什么都不用做，直接点确认。

---

## 边界情况处理

### 情况A：AI 识别到「李梅」，数据库中已有「李梅」
→ 自动匹配，不创建新记录。如果 AI 带来新标签，合并到现有记录。

### 情况B：AI 识别到「李梅」，但数据库中同时有「李梅」和「李梅花」
→ 标记为「🟡 需确认匹配对象」，展开选择器让用户选：
```
🟡 李梅 — 数据库中有多个相似人物
   匹配到: [李梅 ▼] 或 [李梅花 ▼] 或 [新建]
```

### 情况C：AI 识别的关系在数据库中已存在
→ 标记为「重复」，默认取消勾选，显示 `⚠️ 已存在`

### 情况D：AI 置信度低的人物/关系
→ 默认取消勾选，显示 `⚠️ 置信度低`，用户可以手动勾选

### 情况E：解析出 0 个人物/事件
→ 显示「未识别到有效信息，请尝试更详细的描述」

---

## 代码变更清单

### 后端
| 文件 | 变更 |
|------|------|
| `main.py` | 新增 `POST /api/families/{id}/preview` 端点：接收 AI 解析结果，自动匹配/去重，返回预处理后的清单 |

### 前端
| 文件 | 变更 |
|------|------|
| `InboxPanel.tsx` | 完全重写：复选框清单 → 一键入库 |
| `App.tsx` | 解析后调用 preview 端点，入库逻辑简化为一次 API 调用 |
| `api.ts` | 新增 preview 和 batchImport 方法 |

### 关键后端逻辑：`preview` 端点

```python
@app.post("/api/families/{family_id}/preview")
async def preview_import(family_id: str, parsed_data: dict):
    graph = load_family_graph(family_id)
    
    # 1. 人物匹配
    matched_entities = []
    for entity in parsed_data.get("entities", []):
        match = find_best_match(entity["name"], graph.people.values())
        matched_entities.append({
            **entity,
            "matched_person_id": match.id if match else None,
            "matched_person_name": match.name if match else None,
            "action": "skip" if match else "create",
            "checked": True,  # 默认勾选
        })
    
    # 2. 关系去重
    checked_relationships = []
    for rel in parsed_data.get("relationships", []):
        p1 = resolve_id(rel["person1_temp_id"], matched_entities)
        p2 = resolve_id(rel["person2_temp_id"], matched_entities)
        is_dup = any(
            r.person1_id == p1 and r.person2_id == p2 and r.type == rel["type"]
            for r in graph.relationships.values()
        )
        checked_relationships.append({
            **rel,
            "resolved_p1": p1,
            "resolved_p2": p2,
            "is_duplicate": is_dup,
            "checked": not is_dup,  # 重复的不勾选
        })
    
    # 3. 事件（默认勾选）
    checked_events = [{**e, "checked": True} for e in parsed_data.get("events", [])]
    
    return {
        "entities": matched_entities,
        "events": checked_events,
        "relationships": checked_relationships,
    }
```
