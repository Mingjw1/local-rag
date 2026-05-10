# 常用命令速查

## 启动 & 停止

```bash
# 一键启动（自动检测 GPU）
bash up.sh

# 查看所有容器状态
docker compose ps

# 停止所有服务
docker compose down

# 完全重启（重建容器）
docker compose down && docker compose up -d

# 仅重启某个服务
docker compose restart rag-controller
docker compose restart frontend
```

## 查看日志

```bash
# 实时跟踪后端日志
docker compose logs -f rag-controller

# 查看 LLM 日志
docker compose logs -f ollama

# 查看最近 N 行
docker compose logs --tail 50 rag-controller
```

## 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# Ollama 是否正常
curl http://localhost:11434/api/tags

# 向量数据库状态
curl http://localhost:6333/collections/documents

# Qdrant 仪表盘
# http://localhost:6333/dashboard
```

## 文档管理

```bash
# 上传文档
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents \
  -F "file=@doc.pdf" \
  -F "title=文档标题"

# 查看文档列表
curl http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents

# 删除文档
curl -X DELETE http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}
```

## 搜索 & 问答

```bash
# 搜索
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/search \
  -H "Content-Type: application/json" \
  -d '{"query": "你的问题", "top_k": 5}'

# 问答（带引用来源）
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/query \
  -H "Content-Type: application/json" \
  -d '{"query": "你的问题"}'

# 流式问答
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "你的问题"}'
```

## Wiki 维护

```bash
# 触发健康检查（孤儿页、断裂链接）
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/wiki/lint

# 查看 Wiki 页面列表
curl http://localhost:8000/api/v1/knowledge-bases/{kb_id}/wiki/pages

# 查看某个页面
curl http://localhost:8000/api/v1/knowledge-bases/{kb_id}/wiki/pages/{page_id}
```

## 模型管理

```bash
# 查看已下载的模型
docker compose exec ollama ollama list

# 拉取新模型
docker compose exec ollama ollama pull qwen2.5:14b

# 删除模型
docker compose exec ollama ollama rm qwen2.5:7b

# 查看模型列表 API
curl http://localhost:8000/api/v1/admin/models
```

## 配置管理

```bash
# 热加载配置（不重启）
curl -X POST http://localhost:8000/api/v1/admin/reload-config

# 编辑配置后重启
docker compose restart rag-controller
```

## 备份 & 恢复

```bash
# PostgreSQL 备份
docker compose exec postgres pg_dump -U ragkb ragkb > backup_$(date +%Y%m%d).sql

# PostgreSQL 恢复
cat backup_20250510.sql | docker compose exec -T postgres psql -U ragkb ragkb

# Qdrant 快照
curl -X POST 'http://localhost:6333/collections/documents/snapshots'

# Wiki 文件备份
tar czf wiki_backup_$(date +%Y%m%d).tar.gz data/wiki/
```

## 测试 & 调试

```bash
# 导入测试数据
python3 scripts/seed.py

# 运行功能测试
bash scripts/test.sh

# 直接访问 API 文档（Swagger UI）
# http://localhost:8000/docs

# 直接访问 Web UI
# http://localhost:3000
```

## 首次部署

```bash
# 标准环境
bash scripts/setup.sh

# 中国网络环境
bash scripts/setup-china.sh
```
