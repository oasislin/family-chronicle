# 家族编年史 - 数据库设置指南

## 概述

本项目使用两个数据库：
1. **Neo4j** - 图数据库，用于存储家族关系网络
2. **MongoDB** - 文档数据库，用于存储详细信息和媒体文件

## 快速启动

### 1. 安装Docker Desktop

确保已安装Docker Desktop：
- macOS: https://docs.docker.com/desktop/install/mac-install/
- Windows: https://docs.docker.com/desktop/install/windows-install/
- Linux: https://docs.docker.com/desktop/install/linux-install/

### 2. 启动数据库服务

```bash
cd family-chronicle
docker-compose up -d
```

### 3. 验证服务状态

```bash
# 查看运行中的容器
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 访问数据库

#### Neo4j
- **浏览器界面**: http://localhost:7474
- **用户名**: neo4j
- **密码**: family123
- **Bolt连接**: bolt://localhost:7687

#### MongoDB
- **连接字符串**: mongodb://admin:family123@localhost:27017/
- **数据库名**: family_chronicle
- **Mongo Express (Web界面)**: http://localhost:8081

## 数据库结构

### Neo4j (图数据库)

#### 节点类型
- `Person` - 家族成员
- `Event` - 家族事件
- `Family` - 家族
- `User` - 系统用户

#### 关系类型
- `RELATIONSHIP` - 家族关系（包含type属性）
- `PARTICIPATED_IN` - 参与事件
- `HAS_MEMBER` - 家族成员
- `OWNS` - 用户拥有家族

#### Person节点属性
```cypher
{
    id: "person_xxx",
    name: "姓名",
    gender: "male|female|unknown",
    birth_date: "出生日期",
    death_date: "去世日期",
    birth_place: "出生地",
    current_residence: "现居住地",
    tags: ["标签1", "标签2"],
    notes: "备注",
    created_at: "创建时间",
    updated_at: "更新时间"
}
```

### MongoDB (文档数据库)

#### 集合说明
1. `users` - 用户信息
2. `families` - 家族信息
3. `person_details` - 人物详细信息
4. `event_details` - 事件详细信息
5. `media_files` - 媒体文件（照片、文档）
6. `ai_parsing_logs` - AI解析日志
7. `conflict_logs` - 冲突检测日志
8. `user_activity_logs` - 用户活动日志
9. `system_config` - 系统配置

## 数据同步策略

### 双写模式
- **写操作**: 同时写入Neo4j和MongoDB
- **读操作**: 
  - 关系查询 → Neo4j
  - 详细信息查询 → MongoDB
  - 全文搜索 → MongoDB全文索引

### 事务处理
- 使用MongoDB事务保证双写一致性
- 失败时记录到冲突日志，供人工处理

## 备份与恢复

### Neo4j备份
```bash
# 创建备份
docker exec family-chronicle-neo4j neo4j-admin database dump neo4j --to-path=/backups

# 恢复备份
docker exec family-chronicle-neo4j neo4j-admin database load neo4j --from-path=/backups
```

### MongoDB备份
```bash
# 创建备份
docker exec family-chronicle-mongodb mongodump --out=/backups

# 恢复备份
docker exec family-chronicle-mongodb mongorestore /backups
```

## 常见问题

### 1. 端口冲突
如果端口被占用，修改docker-compose.yml中的端口映射：
```yaml
ports:
  - "7475:7474"  # Neo4j HTTP
  - "7688:7687"  # Neo4j Bolt
  - "27018:27017"  # MongoDB
```

### 2. 数据持久化
数据存储在Docker卷中，即使容器停止也不会丢失。要完全重置：
```bash
docker-compose down -v  # 删除卷
docker-compose up -d    # 重新启动
```

### 3. 内存不足
Neo4j需要较多内存，如果遇到内存问题：
```yaml
# 在docker-compose.yml的neo4j服务中添加
environment:
  - NEO4J_server_memory_heap_max__size=1G
  - NEO4J_server_memory_pagecache_size=512M
```

## 开发工具

### Neo4j Browser
访问 http://localhost:7474，使用Cypher语言查询图数据库：
```cypher
// 查看所有人物
MATCH (p:Person) RETURN p LIMIT 25

// 查看某人的所有关系
MATCH (p:Person {name: "王建国"})-[r]-(related)
RETURN p, r, related

// 查看家族树
MATCH path = (ancestor:Person)-[:RELATIONSHIP*1..5]->(descendant:Person)
WHERE ancestor.name = "王大强"
RETURN path
```

### MongoDB Compass
下载MongoDB Compass，连接到mongodb://admin:family123@localhost:27017，可视化管理数据。

## 安全注意事项

1. **生产环境**: 修改默认密码
2. **网络访问**: 限制数据库端口访问
3. **数据加密**: 启用MongoDB和Neo4j的TLS/SSL
4. **备份加密**: 对备份文件进行加密存储

## 下一步

数据库设置完成后，继续执行：
1. 搭建Python后端基础 (Phase 2, Action 4)
2. 接入大模型API (Phase 2, Action 5)
3. 编写冲突检测核心逻辑 (Phase 2, Action 6)