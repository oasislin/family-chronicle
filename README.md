# 📖 家族编年史 — 智能族谱系统

基于 AI 的家族关系管理工具，支持自然语言输入、自动关系推导、交互式图谱可视化。

## 技术栈

- **后端**: Python 3.10+ / FastAPI / JSON 文件存储
- **前端**: React 18 + TypeScript / Tailwind CSS / React Flow
- **AI**: 支持 DeepSeek、智谱 GLM、OpenAI、Anthropic Claude

## 快速开始

### 1. 克隆仓库

```bash
git clone <repo-url>
cd family-chronicle
```

### 2. 后端

```bash
cd backend
cp .env.example .env          # 复制环境变量模板
# 编辑 .env，填入你的 API Key
pip install -r requirements.txt
python main.py                # 启动后端 (http://localhost:8000)
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev                   # 启动前端 (http://localhost:3000)
```

## 项目结构

```
family-chronicle/
├── backend/
│   ├── main.py               # FastAPI 主入口
│   ├── config.py             # 配置管理（环境变量）
│   ├── ai_service.py         # AI 服务（多提供商）
│   ├── relationship_engine.py   # 关系推导引擎
│   ├── conflict_detector.py     # 冲突检测
│   ├── biography_engine.py      # 传记生成
│   ├── history.py               # 编辑历史
│   ├── data/                    # 数据文件（不上传）
│   └── .env.example             # 环境变量模板
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── components/
│       │   ├── FamilyGraph.tsx        # 图谱可视化
│       │   ├── FloatingPersonCard.tsx # 浮动人物卡片
│       │   ├── PersonDetail.tsx       # 人物详情面板
│       │   ├── MessageFeed.tsx        # 消息流
│       │   └── ...
│       └── services/api.ts
├── models.py                 # 数据模型
├── sample_data.json          # 示例数据
└── .gitignore
```

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `AI_PROVIDER` | AI 服务提供商 (`deepseek`/`zhipu`/`openai`/`anthropic`) | 是 |
| `DEEPSEEK_API_KEY` | 华为 ModelArts DeepSeek API Key | 按提供商 |
| `DEEPSEEK_BASE_URL` | API 地址 | 否 |
| `SECRET_KEY` | 应用密钥 | 是 |

详见 `backend/.env.example`。

## ⚠️ 安全提示

- **不要** 将 `.env` 文件提交到 Git
- **不要** 将 `backend/data/` 目录提交到 Git（含个人隐私数据）
- API Key 仅通过环境变量加载，代码中无硬编码
