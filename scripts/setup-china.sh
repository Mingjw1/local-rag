#!/bin/bash
# 中国网络环境专用部署脚本
set -e

echo "=== Local RAG KB MVP — 中国网络部署 ==="

# 1. 配置 Docker 镜像加速
echo ">>> 配置 Docker 镜像加速..."
if [ ! -f /etc/docker/daemon.json ] || ! grep -q "registry-mirrors" /etc/docker/daemon.json 2>/dev/null; then
  echo '请执行以下命令设置 Docker 镜像加速（需要 sudo 密码）：'
  echo ""
  echo '  sudo cp /tmp/daemon.json /etc/docker/daemon.json'
  echo '  sudo systemctl restart docker'
  echo ""
  echo "设置完成后重新运行此脚本。"
  exit 1
else
  echo "✓ Docker 镜像加速已配置"
fi

# 2. 检查 Docker 权限
echo ">>> 检查 Docker 权限..."
if ! docker info >/dev/null 2>&1; then
  echo "Docker 权限不足。请运行: newgrp docker"
  echo "然后重新运行此脚本。"
  exit 1
fi
echo "✓ Docker 权限正常"

# 3. 创建 .env
if [ ! -f .env ]; then
  echo ">>> 创建 .env..."
  cp .env.example .env
  echo "✓ .env 已创建"
fi

# 4. 创建数据目录
mkdir -p data/wiki data/raw data/backup
chmod +x scripts/pull-models.sh

# 5. 拉取 Docker 镜像
echo ">>> 拉取 Docker 镜像..."
docker pull docker.m.daocloud.io/qdrant/qdrant:v1.12.0
docker pull docker.m.daocloud.io/postgres:16-alpine
docker pull docker.m.daocloud.io/redis:7-alpine
docker pull docker.m.daocloud.io/minio/minio:latest
docker pull docker.m.daocloud.io/minio/mc:latest
docker pull docker.m.daocloud.io/python:3.12-slim

# 6. 给镜像打上原始 tag
docker tag docker.m.daocloud.io/qdrant/qdrant:v1.12.0 qdrant/qdrant:v1.12.0
docker tag docker.m.daocloud.io/postgres:16-alpine postgres:16-alpine
docker tag docker.m.daocloud.io/redis:7-alpine redis:7-alpine
docker tag docker.m.daocloud.io/minio/minio:latest minio/minio:latest
docker tag docker.m.daocloud.io/minio/mc:latest minio/mc:latest
docker tag docker.m.daocloud.io/python:3.12-slim python:3.12-slim

echo "✓ 镜像拉取完成"

# 7. 启动服务（使用 up.sh 自动检测 GPU）
echo ">>> 启动服务..."
bash up.sh

echo ""
echo "=== 部署完成 ==="
echo "RAG API:   http://localhost:8000"
echo "API 文档:  http://localhost:8000/docs"
echo "Web UI:    http://localhost:3000"
echo "查看日志:  docker compose logs -f rag-controller"
