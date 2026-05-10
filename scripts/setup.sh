#!/bin/bash
# ==========================================
# 首次安装脚本 — 仅执行一次
# 后续启动请用: bash up.sh
# ==========================================
set -e

cd "$(dirname "$0")/.."

green() { echo -e "\033[32m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }
red() { echo -e "\033[31m$1\033[0m"; }

echo "=== Local RAG KB — 首次安装 ==="

# 1. 检查 Docker
echo ">>> 检查 Docker..."
if ! command -v docker &>/dev/null; then
  red "❌ 未安装 Docker。请先安装："
  echo "   curl -fsSL https://get.docker.com | sh"
  echo "   sudo usermod -aG docker \$USER"
  echo "   然后退出重新登录"
  exit 1
fi
green "✓ Docker: $(docker --version 2>/dev/null || echo '需 newgrp docker 后生效')"

# 2. 检查 Docker Compose
if ! docker compose version &>/dev/null 2>&1; then
  red "❌ Docker Compose 不可用"
  exit 1
fi
green "✓ $(docker compose version)"

# 3. 创建 .env
if [ ! -f .env ]; then
  echo ">>> 创建 .env..."
  cp .env.example .env
  yellow "⚠ 已从 .env.example 创建 .env"
fi

# 4. 创建数据目录
mkdir -p data/wiki data/raw data/backup

# 5. 授予执行权限
chmod +x scripts/pull-models.sh scripts/*.sh up.sh

echo ""
green "========================================"
green "  安装完成！"
green "========================================"
echo ""
echo "后续启动请运行:"
echo ""
echo "  bash up.sh"
echo ""
echo "停止服务:"
echo "  docker compose down"
echo ""
echo "查看运行状态:"
echo "  docker compose ps"
echo ""
echo "查看日志:"
echo "  docker compose logs -f rag-controller"
echo ""
echo "访问地址:"
echo "  Web UI:    http://localhost:3000"
echo "  API 文档:  http://localhost:8000/docs"
echo ""
