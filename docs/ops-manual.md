# Local RAG KB MVP — 运维手册

## 目录

1. [文件结构说明](#1-文件结构说明)
2. [前置条件与环境要求](#2-前置条件与环境要求)
3. [部署指南](#3-部署指南)
4. [日常运维](#4-日常运维)
5. [给客户部署的标准流程](#5-给客户部署的标准流程)
6. [常见问题排查](#6-常见问题排查)

---

## 1. 文件结构说明

```
local-rag-kb-MVP/
│
├── docker-compose.yml            ← 核心！定义所有后台服务
│   包含 6 个容器：Qdrant(向量库) + PostgreSQL(数据库)
│   + Redis(缓存) + MinIO(文件存储) + Ollama(本地LLM) + Frontend(前端)
│
├── Dockerfile                    ← RAG Controller (FastAPI) 的容器构建文件
│
├── .env.example                  ← 环境变量模板，部署时复制为 .env
│
├── config/                       ← 所有配置文件（纯文本，可热加载）
│   ├── rag-controller.yaml       ←   RAG 主配置：数据库连接、缓存、存储
│   ├── models.yaml               ←   模型注册表：定义可用模型
│   └── retrieval.yaml            ←   检索策略：分块大小、搜索参数、生成参数
│
├── app/                          ← Python 后端代码
│   ├── main.py                   ←   程序入口，FastAPI 应用启动
│   │
│   ├── core/
│   │   ├── config.py             ←   配置加载：读 YAML + 环境变量
│   │   ├── models.py             ←   数据模型：定义 API 请求/响应格式
│   │   └── ollama_client.py      ←   Ollama 通信：embedding + 生成
│   │
│   ├── routers/                  ← API 路由（谁访问哪个 URL 对应哪段代码）
│   │   ├── documents.py          ←   文档管理：上传、列表、删除文档
│   │   ├── search.py             ←   搜索问答：搜索、提问、流式回答
│   │   ├── admin.py              ←   管理接口：健康检查、模型列表
│   │   └── wiki.py               ←   Wiki 接口：查看页面、触发 lint
│   │
│   ├── pipeline/                 ← 核心处理逻辑（最重要的目录）
│   │   ├── parsers.py            ←   文档解析：支持 6 种格式
│   │   ├── chunking.py           ←   文本分块：3 种策略
│   │   ├── embedding.py          ←   Embedding 生成
│   │   ├── ingest.py             ←   导入流水线：解析→分块→向量化→存储→Wiki
│   │   └── query.py              ←   搜索问答：检索→重排序→生成回答
│   │
│   ├── db/                       ← 数据库操作
│   │   ├── models.py             ←   定义数据库表结构
│   │   ├── session.py            ←   数据库连接管理
│   │   └── qdrant.py             ←   向量数据库操作
│   │
│   └── wiki/                     ← LLM Wiki 引擎（自动维护知识库）
│       ├── engine.py             ←   Wiki 核心：页面创建、索引维护
│       ├── lint.py               ←   健康检查：孤儿页、断裂链接
│       └── templates/            ←   页面模板（Jinja2）
│
├── frontend/                     ← Web 前端
│   ├── Dockerfile                ←   前端容器构建
│   ├── nginx.conf                ←   反向代理：/api 请求转发给后端
│   ├── package.json              ←   Node.js 依赖
│   ├── tsconfig.json             ←   TypeScript 配置
│   ├── vite.config.ts            ←   开发服务器配置
│   └── src/
│       ├── main.tsx              ←   前端入口
│       ├── App.tsx               ←   主界面：搜索/问答/文档/Wiki 面板
│       └── api.ts                ←   与后端通信的客户端
│
├── scripts/                      ← 运维脚本
│   ├── setup.sh                  ←   一键部署（标准环境）
│   ├── setup-china.sh            ←   一键部署（中国网络）
│   ├── pull-models.sh            ←   Ollama 模型拉取
│   ├── seed.py                   ←   导入测试数据
│   └── test.sh                   ←   快速功能验证
│
├── tests/                        ← 单元测试
│   ├── test_chunking.py          ←   分块逻辑测试
│   ├── test_parsers.py           ←   解析器测试
│   └── test_wiki.py              ←   Wiki 测试
│
└── docs/                         ← 文档
    └── ops-manual.md             ←   本文件
```

---

## 2. 前置条件与环境要求

### 2.1 硬件要求

| 规模 | CPU | 内存 | 硬盘 | GPU（可选） |
|------|-----|------|------|-----------|
| 最小 | 4核 | 8GB | 50GB | 不需要 |
| 推荐 | 8核 | 16GB | 200GB | NVIDIA 显卡（6GB+） |
| 生产 | 16核 | 32GB | 1TB | NVIDIA A100+/多卡 |

**没有 GPU 也能运行**（Ollama 回退到 CPU，速度慢一些），
但 embedding 模型（nomic-embed-text）仅需 4GB 内存，CPU 也能跑。

### 2.2 软件要求

| 软件 | 版本 | 用途 | 安装方式 |
|------|------|------|---------|
| Docker | 24+ | 容器运行 | https://docs.docker.com/engine/install/ |
| Docker Compose | v2+ | 多容器编排 | 通常随 Docker 一起安装 |
| Python (只用 seed 脚本) | 3.12+ | 导入测试数据 | apt / pyenv / conda |
| Git (可选) | 任意 | 版本管理 | apt install git |

### 2.3 网络要求

- **Docker Hub** 可访问（拉取容器镜像）
- **Ollama 模型下载**（首次约 2-10GB 流量）
  - nomic-embed-text: ~274MB
  - qwen2.5:7b: ~4.7GB

**中国大陆用户**：
- Docker 镜像：先配置镜像加速（DaoCloud / 腾讯云）
- Ollama 模型：同上，Ollama 会自动从 GitHub Releases 下载，国内可能慢

### 2.4 端口要求

| 端口 | 服务 | 说明 |
|------|------|------|
| 8000 | RAG Controller API | 后端 API + Swagger 文档 |
| 3000 | Web 前端 | React SPA 界面 |
| 6333 | Qdrant | 向量数据库 API |
| 11434 | Ollama | 本地 LLM API |
| 9000 | MinIO | 对象存储 API |
| 9001 | MinIO Console | 管理控制台 |
| 5432 | PostgreSQL | 数据库（内部访问） |
| 6379 | Redis | 缓存（内部访问） |

---

## 3. 部署指南

### 3.1 标准部署（5 步）

```bash
# 第 1 步：克隆/下载项目
git clone <项目地址> local-rag-kb
cd local-rag-kb

# 第 2 步：首次安装（只需运行一次）
bash scripts/setup.sh

# 第 3 步：一键启动（自动检测 GPU）
bash up.sh

# 第 4 步：导入测试数据
python3 scripts/seed.py

# 第 5 步：验证
bash scripts/test.sh
```

> `up.sh` 会自动检测 AMD GPU（ROCm）→ NVIDIA GPU（CUDA）→ CPU，无需手动选择。

### 3.2 中国网络部署

```bash
# 先配 Docker 镜像加速
sudo cp /tmp/daemon.json /etc/docker/daemon.json
sudo systemctl restart docker

# 然后执行中国专用脚本
cd local-rag-kb
bash scripts/setup-china.sh
```

### 3.3 首次启动后的动作

1. **打开 Web UI**: http://localhost:3000
2. **测试 API**: http://localhost:8000/docs （交互式 API 文档）
3. **查看向量数据库**: http://localhost:6333/dashboard
4. **上传真实文档**: 在 Web UI 的 "文档" 面板上传

### 3.4 Ollama 模型说明

首次启动会自动拉取 2 个模型（约 5GB）：

| 模型 | 大小 | 用途 |
|------|------|------|
| `nomic-embed-text` | 274MB | 将文本转为向量 |
| `qwen2.5:7b` | 4.7GB | 生成回答 |

如果想换模型，编辑 `config/models.yaml` 和 `.env` 中的模型名，
然后 `ollama pull <新模型名>` 即可。

---

## 4. 日常运维

### 4.1 查看服务状态

```bash
docker compose ps                    # 所有服务状态
docker compose logs -f rag-controller # 查看后端日志（实时）
docker compose logs -f ollama        # 查看 LLM 日志
```

### 4.2 重启服务

```bash
docker compose restart rag-controller  # 重启后端（不改代码时用）
docker compose restart frontend        # 重启前端
docker compose down && docker compose up -d  # 完全重启
```

### 4.3 更新配置

编辑 `config/*.yaml` 后，发送 SIGHUP 信号：

```bash
# 方式 1：API 触发（推荐）
curl -X POST http://localhost:8000/api/v1/admin/reload-config

# 方式 2：重启服务
docker compose restart rag-controller
```

### 4.4 备份数据

```bash
# Qdrant 备份
curl -X POST 'http://localhost:6333/collections/documents/snapshots'

# PostgreSQL 备份
docker compose exec postgres pg_dump -U ragkb ragkb > backup_$(date +%Y%m%d).sql

# Wiki 备份（就是 markdown 文件）
tar czf wiki_backup_$(date +%Y%m%d).tar.gz data/wiki/
```

### 4.5 导入文档

```bash
# 通过 API 上传
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents \
  -F "file=@doc.pdf" \
  -F "title=文档标题"

# 通过 Web UI
# 打开 http://localhost:3000 → 文档面板 → 上传
```

### 4.6 Wiki 维护

```bash
# 触发 Lint 健康检查
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/wiki/lint

# 查看 Wiki 页面列表
curl http://localhost:8000/api/v1/knowledge-bases/{kb_id}/wiki/pages

# 查看某个页面
curl http://localhost:8000/api/v1/knowledge-bases/{kb_id}/wiki/pages/{page_id}
```

### 4.7 性能调优

如果响应慢，检查以下配置：

1. **分块大小**（`config/retrieval.yaml` 中 `chunking.strategies.recursive.chunk_size`）
   - 调小（256）→ 更快的搜索，但上下文碎片化
   - 调大（1024）→ 更完整的上下文，但搜索变慢

2. **Top-K 数量**（同上，`search.top_k`）
   - 调小（5）→ 速度快，可能漏结果
   - 调大（20）→ 更全，但 LLM 处理更多上下文

3. **开启缓存**（默认开启）
   - embedding cache：相同文本不重复计算
   - query cache：相同问题直接返回（5 分钟有效）

---

## 5. 给客户部署的标准流程

### 第 0 步：需求确认（10分钟电话）

确认客户环境：

| 问题 | 意义 |
|------|------|
| 操作系统？ | Linux 首选，Windows/Mac 也可用 Docker |
| 有没有 GPU？ | 没有也能跑，但回答速度慢 2-5 倍 |
| 网络能不能访问 Docker Hub？ | 国内需要镜像加速 |
| 客户有什么文档？ | PDF / Word / Markdown / 网页？ |
| 用于什么场景？ | 客服 / 内部知识库 / 法律文档？ |

### 第 1 步：准备工作（30分钟）

```bash
# 在客户服务器上执行：

# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. 退出重新登录，或 newgrp docker
newgrp docker

# 3. （国内用户）配置镜像加速
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io"]
}
EOF
sudo systemctl restart docker

# 4. 安装 Python（用于导入脚本）
# Debian/Ubuntu: sudo apt install python3 python3-pip
```

### 第 2 步：部署系统（15分钟）

```bash
# 把项目传到客户机器（scp / U盘 / git clone）
scp -r local-rag-kb-MVP/ user@client-server:~/

cd local-rag-kb-MVP

# 部署
bash up.sh
```

### 第 3 步：配置模型（10分钟）

如果客户有 GPU，可以换更好的模型：

```bash
# 拉取更大的模型
docker compose exec ollama ollama pull qwen2.5:14b  # 更好的回答质量
docker compose exec ollama ollama pull bge-m3        # 更好的中文 embedding

# 编辑 config/models.yaml 修改 default 模型名
```

如果客户没有 GPU（CPU 运行）：

- 保持默认的 `qwen2.5:7b`（量化后 8GB 内存也能跑）
- 或者换更小的 `qwen2.5:3b` 或 `phi3:mini`

### 第 4 步：导入文档（时间取决于文档量）

```bash
# 方式 1：Web UI 上传（适合少量文档）
# 打开 http://客户IP:3000 → 文档 → 上传

# 方式 2：API 批量导入
python3 -m pip install httpx
# 编写批量导入脚本（参考 scripts/seed.py）
```

### 第 5 步：验证交付（5分钟）

检查清单：

```
□ http://客户IP:3000 可打开并显示 Web 界面
□ 上传测试文档后，搜索返回结果
□ 问答能正常生成回答（含引用来源）
□ Wiki 面板能看到自动生成的页面
□ API 文档 http://客户IP:8000/docs 可访问
□ 重启服务器后服务自动恢复（docker compose restart）
```

### 第 6 步：给客户的最终交付物

```
交付清单:
├── 项目文件（整个目录拷贝给客户）
│   └── local-rag-kb-MVP/
├── 文档
│   └── docs/ops-manual.md
├── 客户需要知道的信息
│   ├── 访问地址: http://服务器IP:3000
│   ├── API 文档: http://服务器IP:8000/docs
│   └── 管理员密码: .env 文件中配置
└── 联系方式
    └── 技术支持微信/电话
```

---

## 6. 常见问题排查

### Q1: Docker 拉取镜像超时

```
Error: failed to resolve reference "docker.io/...": i/o timeout
```

**原因**：国内网络访问 Docker Hub 不稳定
**解决**：

```bash
# 方案 1：配置镜像加速
sudo tee /etc/docker/daemon.json <<-'EOF'
{"registry-mirrors": ["https://docker.m.daocloud.io"]}
EOF
sudo systemctl restart docker

# 方案 2：从镜像拉取后重新 tag
docker pull docker.m.daocloud.io/qdrant/qdrant:v1.12.0
docker tag docker.m.daocloud.io/qdrant/qdrant:v1.12.0 qdrant/qdrant:v1.12.0
```

### Q2: 问答返回空或错误

**原因 1**: Ollama 模型未就绪

```bash
# 检查 Ollama 状态
docker compose logs ollama
# 确保能看到 "done" 表示模型已加载
```

**原因 2**: 没有文档或搜索不到

```bash
# 检查 Qdrant 中是否有数据
curl http://localhost:6333/collections/documents
```

### Q3: Web UI 打不开

```bash
# 检查前端是否运行
docker compose ps frontend

# 检查前端日志
docker compose logs frontend

# 如果是显示空白页，可能是 API 代理问题
# 直接访问 API 试试
curl http://localhost:8000/health
```

### Q4: 文档导入失败

```bash
# 检查文档解析器是否支持该格式
# 支持的格式：.md .txt .pdf .docx .html .xlsx .csv

# 查看后端日志
docker compose logs rag-controller

# 常见原因：PDF 解析需要额外依赖
# 尝试先把 PDF 转为 Markdown
```

### Q5: 如何升级

```bash
# 备份数据
docker compose exec postgres pg_dump -U ragkb ragkb > pre_upgrade.sql
curl -X POST 'http://localhost:6333/collections/documents/snapshots'

# 拉取新代码
git pull

# 重新构建并启动
docker compose down
docker compose build rag-controller
docker compose up -d
```

### Q6: Ollama 显存不足

```bash
# 错误: CUDA out of memory

# 解决：换小模型
# 编辑 .env:
OLLAMA_GENERATION_MODEL=qwen2.5:3b

# 或者纯 CPU 运行（移除 GPU 配置）
# 编辑 docker-compose.yml，删除 ollama 服务的 deploy.resources 部分
```
