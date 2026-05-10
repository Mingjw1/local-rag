"""Embedding 生成 — 通过 Ollama 调用"""

import hashlib
from typing import List

from app.core.config import settings
from app.core.ollama_client import ollama_client


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


async def generate_embeddings(
    texts: List[str],
    model: str | None = None,
    use_cache: bool = True,
) -> List[List[float]]:
    """批量生成文本的 embedding 向量

    支持 LRU 缓存（基于文本 hash），减少重复调用
    """
    model = model or settings.ollama_embedding_model
    cache_config = settings.retrieval_config.get("embedding", {}).get("cache", {})
    cache_enabled = use_cache and cache_config.get("enabled", True)

    # 注：完整缓存需要 Redis，这里简化使用内存字典
    # 生产环境应使用 Redis：hash → embedding
    _embedding_cache: dict[str, list[float]] = {}

    uncached_indices: list[int] = []
    uncached_texts: list[str] = []
    results: list[list[float] | None] = [None] * len(texts)

    for i, text in enumerate(texts):
        if cache_enabled:
            h = _text_hash(text)
            cached = _embedding_cache.get(h)
            if cached:
                results[i] = cached
                continue
            uncached_indices.append(i)
            uncached_texts.append(text)
        else:
            uncached_indices.append(i)
            uncached_texts.append(text)

    # 调用 Ollama batch embedding
    if uncached_texts:
        embeddings = await ollama_client.embed_batch(uncached_texts, model)
        for idx, emb in zip(uncached_indices, embeddings):
            results[idx] = emb
            if cache_enabled:
                h = _text_hash(texts[idx])
                _embedding_cache[h] = emb

    return [r for r in results if r is not None]
