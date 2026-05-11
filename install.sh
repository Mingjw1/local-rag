#!/bin/bash
# ==========================================
# Local RAG KB — 一键安装启动脚本
# 自动检测 GPU 类型，无需手动配置
# 使用方式: bash install.sh
# ==========================================
set -e

cd "$(dirname "$0")"

GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
NC='\033[0m'

green()  { echo -e "${GREEN}$1${NC}"; }
yellow() { echo -e "${YELLOW}$1${NC}"; }
red()    { echo -e "${RED}$1${NC}"; }

echo ""
green "========================================"
green "  Local RAG KB — 一键安装"
green "========================================"
echo ""

# === 1. 检查 Docker ===
echo ">>> 检查 Docker..."
if ! command -v docker &>/dev/null; then
  red "❌ 未安装 Docker。请先安装："
  echo "   curl -fsSL https://get.docker.com | sh"
  echo "   sudo usermod -aG docker \$USER"
  echo "   然后退出重新登录"
  exit 1
fi
green "  ✓ Docker: $(docker --version 2>/dev/null || echo 'OK')"

# === 2. 检查 Docker Compose ===
if ! docker compose version &>/dev/null 2>&1; then
  red "❌ Docker Compose 不可用"
  exit 1
fi
green "  ✓ $(docker compose version)"

# === 3. 创建数据目录 ===
mkdir -p data/wiki data/raw data/backup
green "  ✓ 数据目录已创建"

# === 4. 创建 .env（如果不存在）===
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    yellow "  ⚠ 已从 .env.example 创建 .env"
    yellow "  ⚠ 请根据需要修改 .env 中的配置"
  else
    yellow "  ⚠ 未找到 .env.example，跳过"
  fi
else
  green "  ✓ .env 已存在"
fi

# === 5. 检测 GPU ===
detect_gpu() {
  if [ -e /dev/kfd ] && command -v rocminfo &>/dev/null; then
    echo "amd"
    return
  fi
  if command -v nvidia-smi &>/dev/null; then
    echo "nvidia"
    return
  fi
  echo "cpu"
}

GPU=$(detect_gpu)
COMPOSE_FILES="-f docker-compose.yml"

case "$GPU" in
  amd)
    if getent group video >/dev/null 2>&1; then
      export VIDEO_GID=$(getent group video | cut -d: -f3)
      export RENDER_GID=$(getent group render | cut -d: -f3)
      COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.amd.yml"
      green "  ✓ 检测到 AMD GPU — 启用 ROCm 加速"
    else
      yellow "  ⚠ AMD GPU 检测到但缺少 video/render 组，使用 CPU 模式"
      GPU="cpu"
    fi
    ;;
  nvidia)
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.nvidia.yml"
    green "  ✓ 检测到 NVIDIA GPU — 启用 CUDA 加速"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1
    ;;
  *)
    yellow "  ⚠ 未检测到 GPU，使用 CPU 模式"
    ;;
esac

echo ""

# === 6. 启动服务 ===
green "========================================"
green "  启动 Local RAG KB ($GPU 模式)"
green "========================================"
echo ""

docker compose $COMPOSE_FILES up -d

echo ""
green "✓ 服务已启动！"
echo ""
echo "  访问地址:"
echo "    Web UI:    http://localhost:3000"
echo "    API 文档:  http://localhost:8000/docs"
echo ""
echo "  常用命令:"
echo "    查看日志:    docker compose logs -f rag-controller"
echo "    停止服务:    docker compose down"
echo "    重启服务:    docker compose restart"
echo ""
echo "注意：首次启动需要拉取 Ollama 模型（约 4GB），"
echo "  请耐心等待。查看进度：docker compose logs -f ollama"
echo ""
