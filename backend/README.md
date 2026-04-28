# 家族编年史 - 后端API

## 概述

基于FastAPI构建的RESTful API后端，提供家族数据管理、AI解析、冲突检测等功能。

## 快速开始

### 1. 安装依赖

```bash
cd family-chronicle/backend
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 应用配置
DEBUG=true
SECRET_KEY=your-secret-key-here

# 数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=family123

MONGODB_URI=mongodb://admin:family123@localhost:27017/
MONGODB_DATABASE=family_chronicle

# AI服务配置
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 隐私设置
PRIVACY_MODE=local_only
ENABLE_DESENSITIZATION=true
```

### 3. 启动服务器

```bash
python main.py
```

或者使用uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问API文档

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## API端点

### 基础接口

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/` | 根路径，返回API信息 |
| GET | `/api/health` | 健康检查 |

### 家族管理

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/families` | 创建新家族 |
| GET | `/api/families` | 获取家族列表 |

### 人物管理

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/families/{family_id}/people` | 创建新人物 |
| GET | `/api/families/{family_id}/people` | 获取人物列表 |
| GET | `/api/families/{family_id}/people/{person_id}` | 获取人物详情 |

### 事件管理

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/families/{family_id}/events` | 创建新事件 |
| GET | `/api/families/{family_id}/events` | 获取事件列表 |

### 关系管理

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/families/{family_id}/relationships` | 创建新关系 |
| GET | `/api/families/{family_id}/relationships` | 获取关系列表 |

### AI解析

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/ai/parse` | 使用AI解析自然语言文本 |
| GET | `/api/ai/prompt` | 获取解析提示词（调试用） |

### 冲突检测

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/conflict/check` | 检查数据冲突 |

### 数据导入导出

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/families/{family_id}/import` | 导入家族数据 |
| GET | `/api/families/{family_id}/export` | 导出家族数据 |

## 使用示例

### 创建家族

```bash
curl -X POST "http://localhost:8000/api/families?name=王氏家族"
```

### 创建人物

```bash
curl -X POST "http://localhost:8000/api/families/family_20240101_120000/people" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "王建国",
    "gender": "male",
    "birth_date": "1980-12-08",
    "tags": ["老二", "手艺人"],
    "current_residence": "县城"
  }'
```

### AI解析

```bash
curl -X POST "http://localhost:8000/api/ai/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "大伯的老二建国，95年和李梅二婚了，后来认了村长赵大爷做干爹"
  }'
```

## 项目结构

```
backend/
├── main.py              # FastAPI主应用
├── config.py            # 配置管理
├── requirements.txt     # 依赖列表
├── test_api.py          # API测试脚本
├── data/                # 数据存储目录
└── logs/                # 日志目录
```

## 开发指南

### 添加新的API端点

1. 在`main.py`中添加新的路由函数
2. 使用Pydantic模型定义请求/响应格式
3. 添加适当的错误处理
4. 更新API文档

### 数据库集成

当前版本使用JSON文件存储数据。要集成数据库：

1. 取消注释`requirements.txt`中的数据库驱动
2. 在`config.py`中配置数据库连接
3. 创建数据库连接模块
4. 修改数据访问层代码

### AI服务集成

要接入实际的AI服务：

1. 在`config.py`中配置API密钥
2. 创建AI服务客户端模块
3. 修改`/api/ai/parse`端点的实现
4. 添加错误处理和重试逻辑

## 测试

运行测试脚本：

```bash
# 先启动API服务器
python main.py

# 在另一个终端运行测试
python test_api.py
```

## 部署

### 生产环境部署

1. 使用Gunicorn作为WSGI服务器：
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

2. 配置Nginx反向代理
3. 设置SSL证书
4. 配置进程管理（systemd/supervisor）

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 故障排除

### 常见问题

1. **端口被占用**
   - 修改`main.py`中的端口号
   - 或使用`--port`参数指定其他端口

2. **数据库连接失败**
   - 检查数据库服务是否启动
   - 验证连接配置是否正确

3. **AI API调用失败**
   - 检查API密钥是否正确
   - 验证网络连接是否正常

4. **权限问题**
   - 确保数据目录有写入权限
   - 检查日志文件权限

## 下一步

1. 集成实际的AI服务
2. 添加用户认证和授权
3. 实现数据库持久化
4. 添加文件上传功能
5. 实现WebSocket实时更新