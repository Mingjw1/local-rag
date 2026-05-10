#!/bin/bash
# ╔══════════════════════════════════════════╗
# ║  已弃用 — 请使用根目录的 up.sh           ║
# ║  bash up.sh（自动检测 AMD / NVIDIA/CPU） ║
# ╚══════════════════════════════════════════╝
echo "⚠ 此脚本已弃用，请使用: bash up.sh"
echo "  （up.sh 会自动检测 AMD/NVIDIA/CPU，无需手动选择）"
exec bash "$(dirname "$0")/../up.sh"
