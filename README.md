# 📖 家族编年史 — 智能族谱系统

基于 AI 的家族关系管理工具，支持自然语言输入、自动关系推导、交互式图谱可视化。本项目旨在通过大语言模型（LLM）实现零门槛的家族数据录入与管理。

## 核心特性

- **🚀 交互式自然语言提取**: 采用“解析-确认-入库”三段式流程，基于 Phase 3 架构，强制 source_ref 方向一致性。
- **🧠 逻辑主权编译引擎 (CompilerEngine)**: 采用“事件溯源 (Event Sourcing)”架构。所有操作均记录为事实，动态编译成图。
- **🛡️ 铁律级冲突检测**: 实时检测血缘环路、代际跳跃及父母唯一性冲突。严禁任何逻辑违规数据进入数据库。
- **📊 动态可视化聚焦**: 基于 React Flow，支持选中人物自动居中、非关联节点交互式淡化，突出核心血缘脉络。
- **👻 智能占位符推导**: 自动识别并创建推导中的中间节点（占位人物），支持自动性别推导。

## 技术栈

- **后端**: Python 3.10+ / FastAPI / 事件溯源 (Fact Log) / 深度拓扑分析 (DFS)
- **前端**: React 18 + TypeScript / Tailwind CSS / React Flow (v11) / useReactFlow 状态管理
- **AI**: 针对中文亲属语义优化的 Prompt Engineering，支持 DeepSeek/GLM 等主流模型

## 快速开始

### 1. 克隆仓库

```bash
git clone <repo-url>
cd family-chronicle
```

### 2. 后端配置

```bash
cd backend
cp .env.example .env          # 复制环境变量模板
# 编辑 .env，填入你的 API Key 和 Provider 信息
pip install -r requirements.txt
python main.py                # 启动后端 (默认端口: 8000)
```

### 3. 前端配置

```bash
cd frontend
npm install
npm run dev                   # 启动前端 (默认端口: 3000)
```

## 项目结构

```
family-chronicle/
├── backend/
│   ├── main.py               # API 路由与逻辑熔断层
│   ├── compiler_engine.py    # 逻辑主权引擎 (核心：负责事实编译与约束校验)
│   ├── fact_store.py         # 基于 JSON 的事件溯源事实存储库
│   ├── ai_service.py         # AI 核心抽象层
│   └── data/                 # 家族 Fact Log JSON 数据存储
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── FamilyGraph.tsx        # 族谱可视化画布 (支持居中聚焦/高亮淡化)
│       │   ├── ExtractionConfirmCard.tsx # AI 提取结果确认卡片
│       │   └── PersonNode.tsx         # 深度自定义人物节点
│       └── App.tsx                    # 前端逻辑入口与状态分发
├── prompt_engineering.py      # AI 提取指令集 (含方向性约束铁律)
├── models.py                  # 统一的数据模型定义
└── README.md
```

## 环境变量说明

| 变量 | 说明 | 必填 |
|------|------|------|
| `AI_PROVIDER` | AI 服务提供商 (`deepseek`/`zhipu`/`openai`) | 是 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 按需 |
| `DEEPSEEK_BASE_URL` | API Base URL | 否 |
| `LOG_LEVEL` | 日志级别 (DEBUG/INFO/ERROR) | 否 |

## ⚠️ 开发注意事项

- **本地稳定性**: 本项目包含大量依赖和扫描项，建议在 IDE 中配置忽略 `node_modules`、`dist`、`.git` 等目录以防 AI 助手进程溢出。
- **数据备份**: 定期备份 `backend/data/` 下的 JSON 文件。
- **隐私**: 请勿将包含真实家族成员信息的 JSON 数据上传至公共仓库。
