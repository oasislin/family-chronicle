# 📖 家族编年史 — 智能族谱系统

基于 AI 的家族关系管理工具，支持自然语言输入、自动关系推导、交互式图谱可视化。本项目旨在通过大语言模型（LLM）实现零门槛的家族数据录入与管理。

## 核心特性

- **🚀 交互式自然语言提取**: 采用“解析-确认-入库”三段式流程，确保 AI 提取的数据准确无误，防止幻觉。
- **🧠 扩散式关系推导 (v2)**: 基于 BFS 算法的推导引擎，能够根据已有的父子、配偶关系自动补全庞大的家族关系网（如祖孙、兄弟姐妹、叔侄等）。
- **🛡️ 冲突检测与数据对齐**: 实时检测录入数据与已有图谱的逻辑冲突，支持实体对齐（Reconciliation）防止重复创建人物。
- **📊 动态可视化**: 基于 React Flow 的交互式族谱图，支持人物拖拽、详情查看及生平传记展示。
- **📝 生平自动生成**: 根据家族图谱中的事件和关系，利用 AI 自动撰写人物传记。

## 技术栈

- **后端**: Python 3.10+ / FastAPI / JSON 文件存储 / Loguru 日志
- **前端**: React 18 + TypeScript / Tailwind CSS / React Flow / Lucide Icons
- **AI**: 支持 DeepSeek (通过华为 ModelArts)、智谱 GLM、OpenAI、Anthropic Claude

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
│   ├── main.py               # FastAPI 主入口及路由
│   ├── config.py             # 环境变量与提供商配置
│   ├── ai_service.py         # AI 核心抽象层
│   ├── derivation_engine_v2.py  # BFS 扩散式关系推导引擎
│   ├── conflict_detector.py     # 逻辑冲突检测
│   ├── biography_engine.py      # AI 传记生成引擎
│   ├── relationship_validator.py # 关系合法性校验与自动修复
│   ├── history.py               # 操作审计与历史追踪
│   └── data/                    # 家族 JSON 数据存储
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── FamilyGraph.tsx        # 族谱可视化画布
│       │   ├── ExtractionConfirmCard.tsx # AI 提取结果确认卡片 (核心)
│       │   ├── MessageFeed.tsx        # 交互式对话流
│       │   └── PersonDetail.tsx       # 人物详情侧边栏
│       └── services/api.ts            # 前端 API 调用封装
├── models.py                 # 统一的数据模型定义 (Pydantic/Dataclass)
├── .antigravityignore        # AI Agent 防崩溃忽略配置
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
