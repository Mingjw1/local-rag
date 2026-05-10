"""文档分块策略"""

import re
from typing import List

from app.core.config import settings


def chunk_text(text: str, strategy: str = "recursive") -> List[str]:
    """按策略对文本分块"""
    config = settings.retrieval_config.get("chunking", {})
    strategies = config.get("strategies", {})

    if strategy == "recursive" or strategy not in strategies:
        return _recursive_chunk(text, strategies.get("recursive", {}))
    elif strategy == "semantic":
        return _semantic_chunk(text, strategies.get("semantic", {}))
    elif strategy == "code_aware":
        return _code_aware_chunk(text, strategies.get("code_aware", {}))
    return _recursive_chunk(text, strategies.get("recursive", {}))


def _recursive_chunk(text: str, config: dict) -> List[str]:
    """递归字符分块 — 通用策略"""
    chunk_size = config.get("chunk_size", 512)
    chunk_overlap = config.get("chunk_overlap", 64)
    separators = config.get("separators", ["\n\n", "\n", "。", ".", " ", ""])

    chunks = []
    current = text

    if len(current) <= chunk_size:
        return [current.strip()]

    while current:
        if len(current) <= chunk_size:
            chunks.append(current.strip())
            break

        # 尝试在各个分隔符位置切分
        split_point = -1
        for sep in separators:
            if sep == "":  # 最后一个兜底
                split_point = chunk_size
                break
            pos = current.rfind(sep, 0, chunk_size)
            if pos > 0:
                split_point = pos + len(sep)
                break

        if split_point <= 0:
            split_point = chunk_size

        chunks.append(current[:split_point].strip())
        current = current[split_point - chunk_overlap:] if chunk_overlap > 0 else current[split_point:]

    return [c for c in chunks if c]


def _semantic_chunk(text: str, config: dict) -> List[str]:
    """语义分块 — 按句子边界分割，合并到 chunk_size 范围"""
    min_size = config.get("min_chunk_size", 128)
    max_size = config.get("max_chunk_size", 1024)

    # 按句子分
    sentences = re.split(r'(?<=[。！？.!?])\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_size:
            current_chunk += sentence
        else:
            if len(current_chunk) >= min_size:
                chunks.append(current_chunk.strip())
            current_chunk = sentence

    if current_chunk and len(current_chunk) >= min_size:
        chunks.append(current_chunk.strip())

    # 如果最后一段太小，合并到前一段
    if chunks and len(chunks[-1]) < min_size and len(chunks) > 1:
        chunks[-2] = chunks[-2] + chunks[-1]
        chunks.pop()

    return chunks


def _code_aware_chunk(text: str, config: dict) -> List[str]:
    """代码文档分块 — 保留代码块完整性"""
    chunk_size = config.get("chunk_size", 1024)
    max_code_lines = config.get("max_code_block_lines", 200)

    # 分离代码块和普通文本
    parts = re.split(r'(```[\w]*\n.*?```)', text, flags=re.DOTALL)
    chunks = []
    current_text = ""

    for part in parts:
        if part.startswith("```"):
            # 代码块单独作为一个 chunk（如果太大则截断）
            code_lines = part.split("\n")
            if len(code_lines) > max_code_lines:
                part = "\n".join(code_lines[:max_code_lines]) + "\n<!-- 代码块截断 -->"
            if current_text.strip():
                chunks.extend(_recursive_chunk(current_text, {"chunk_size": chunk_size, "chunk_overlap": 32}))
                current_text = ""
            chunks.append(part.strip())
        else:
            current_text += part

    if current_text.strip():
        chunks.extend(_recursive_chunk(current_text, {"chunk_size": chunk_size, "chunk_overlap": 32}))

    return chunks


def chunk_document(content: str, content_type: str) -> List[str]:
    """根据文档类型选择分块策略"""
    if content_type == "text/markdown":
        # Markdown 可能含代码块
        return _code_aware_chunk(content, {})
    elif content_type == "text/plain":
        return _recursive_chunk(content, {})
    elif "code" in content_type or "python" in content_type or "javascript" in content_type:
        return _code_aware_chunk(content, {})
    else:
        return _recursive_chunk(content, {})
