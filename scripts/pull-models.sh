#!/bin/sh
# Ollama 模型拉取脚本
# 仅当模型不存在时才拉取

has_model() {
  ollama list 2>/dev/null | grep -q "^$1[[:space:]]"
}

echo "Checking embedding model: nomic-embed-text..."
has_model nomic-embed-text || ollama pull nomic-embed-text

echo "Checking generation model: qwen2.5:7b..."
has_model qwen2.5:7b || ollama pull qwen2.5:7b

echo "All models ready!"
