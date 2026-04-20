# 家族编年史 - 前端应用

基于 React + TypeScript + React Flow 构建的智能族谱可视化前端。

## 功能特性

- 🕸️ **图谱可视化** - 使用 React Flow 展示家族关系网络
- 🎙️ **随手记录** - 输入自然语言描述，AI 自动解析
- 📥 **待办校正台** - 冲突检测结果展示与处理
- 👤 **人物详情** - 点击节点查看个人时间线
- 🔍 **搜索功能** - 快速查找家族成员

## 技术栈

- React 18 + TypeScript
- React Flow (图谱可视化)
- Tailwind CSS (样式)
- Vite (构建工具)
- Axios (HTTP 客户端)

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动后端服务

```bash
cd backend
python main.py
```

后端将在 http://localhost:8000 启动。

### 3. 启动前端开发服务器

```bash
cd frontend
npm run dev
```

前端将在 http://localhost:3000 启动，并自动代理 API 请求到后端。

## 项目结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── FamilyGraph.tsx    # 图谱可视化组件
│   │   ├── InputPanel.tsx     # 输入面板组件
│   │   ├── InboxPanel.tsx     # 待办校正台组件
│   │   └── PersonDetail.tsx   # 人物详情面板组件
│   ├── services/
│   │   └── api.ts             # API 服务封装
│   ├── types.ts               # TypeScript 类型定义
│   ├── App.tsx                # 主应用组件
│   ├── main.tsx               # 入口文件
│   └── index.css              # 全局样式
├── public/
│   └── favicon.svg            # 应用图标
├── index.html                 # HTML 模板
├── package.json               # 项目配置
├── vite.config.ts             # Vite 配置
├── tailwind.config.js         # Tailwind 配置
├── postcss.config.js          # PostCSS 配置
├── tsconfig.json              # TypeScript 配置
└── tsconfig.node.json         # Node TypeScript 配置
```

## 使用说明

### 1. 输入家族叙事

在左侧输入框中输入家族故事，例如：

> 王建国是家里的老二，1980年出生在王家村。他认了村长赵大爷做干爹。1995年娶了隔壁村的李梅，这是他的二婚。

点击"AI解析"按钮或使用 `⌘+Enter` 快捷键。

### 2. 查看冲突检测

系统会自动检测数据冲突：
- 🟢 **无冲突** - 可直接入库
- 🟡 **语义模糊** - 需要手动确认
- 🔴 **逻辑冲突** - 需修正后入库

### 3. 管理待入库数据

在右侧待办校正台中：
- 查看冲突详情
- 选择解决方案
- 一键入库无冲突数据

### 4. 图谱交互

- 点击节点查看人物详情
- 拖拽节点调整布局
- 缩放和移动画布
- 使用搜索框快速定位

## 关系类型说明

| 类型 | 颜色 | 说明 |
|------|------|------|
| 亲子关系 | 蓝色 | 父母与子女 |
| 配偶 | 粉色(动画) | 夫妻关系 |
| 兄弟姐妹 | 绿色 | 同胞关系 |
| 祖孙 | 紫色 | 祖辈与孙辈 |
| 干亲 | 靛蓝 | 认干爹/干儿子 |
| 过继 | 橙色 | 过继关系 |
| 姻亲 | 灰色 | 婚姻产生的亲属 |

## 开发

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。

### 预览生产构建

```bash
npm run preview
```

## API 代理

开发模式下，所有 `/api` 开头的请求会自动代理到 `http://localhost:8000`。

配置在 `vite.config.ts` 中：

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```
