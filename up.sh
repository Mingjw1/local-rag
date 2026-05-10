#!/bin/bash
# ==========================================
# Local RAG KB — 一键启动脚本
# 自动检测 AMD / NVIDIA / CPU，无需手动配置
# ==========================================
set -e

cd "$(dirname "$0")"

# 颜色
green() { echo -e "\033[32m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }

# 检测 GPU 类型
detect_gpu() {
  # 检测 AMD GPU（ROCm）
  if [ -e /dev/kfd ] && command -v rocminfo &>/dev/null; then
    echo "amd"
    return
  fi
  # 检测 NVIDIA GPU
  if command -v nvidia-smi &>/dev/null; then
    echo "nvidia"
    return
  fi
  # 默认 CPU
  echo "cpu"
}

GPU=$(detect_gpu)

case "$GPU" in
  amd)
    VIDEO_GID=$(getent group video | cut -d: -f3)
    RENDER_GID=$(getent group render | cut -d: -f3)
    if [ -z "$VIDEO_GID" ] || [ -z "$RENDER_GID" ]; then
      yellow "⚠ AMD GPU 检测到但缺少 video/render 组，降级为 CPU 模式"
      GPU="cpu"
    else
      export VIDEO_GID
      export RENDER_GID
      green "✓ 检测到 AMD GPU — 启用 ROCm 加速 (video=$VIDEO_GID, render=$RENDER_GID)"
    fi
    ;;
  nvidia)
    green "✓ 检测到 NVIDIA GPU — 启用 CUDA 加速"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1
    ;;
  *)
    yellow "⚠ 未检测到 GPU，使用 CPU 模式（回答速度较慢）"
    ;;
esac

# 确保 .env 存在
if [ ! -f .env ]; then
  cp .env.example .env
  yellow "⚠ 已从 .env.example 创建 .env，请根据需要修改配置"
fi

# 创建数据目录
mkdir -p data/wiki data/raw data/backup

# 选择 docker-compose 配置文件
COMPOSE_FILES="-f docker-compose.yml"
case "$GPU" in
  amd)    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.amd.yml" ;;
  nvidia) COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.nvidia.yml" ;;
esac

# 启动
echo ""
green "========================================"
green "  启动 Local RAG KB ($GPU 模式)"
green "========================================"
echo ""

exec docker compose $COMPOSE_FILES up -d
