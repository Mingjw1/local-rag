"""搜索和问答流水线"""

from typing import List, AsyncGenerator

from app.core.config import settings
from app.core.models import SearchResult
from app.core.ollama_client import ollama_client
from app.db.qdrant import qdrant_client


async def search_documents(
    query: str,
    kb_id: str,
    top_k: int = 5,
    score_threshold: float | None = None,
    hybrid: bool = True,
) -> List[SearchResult]:
    """搜索相关文档块

    Args:
        query: 用户查询
        kb_id: 知识库 ID
        top_k: 返回结果数
        score_threshold: 最小相似度阈值
        hybrid: 是否使用混合搜索（向量 + BM25）

    Returns:
        SearchResult 列表
    """
    from app.core.ollama_client import ollama_client

    # 1. 生成查询 embedding
    query_embedding = await ollama_client.embed(query)

    # 2. 在 Qdrant 中搜索（不设分数阈值，全部返回让 LLM 筛选）
    search_config = settings.retrieval_config.get("search", {})
    final_top_k = search_config.get("rerank_top_k", top_k)

    collection = settings.rag_config["vector_db"]["collection_name"]

    # 构建过滤条件（按知识库）
    filter_condition = {"must": [{"key": "kb_id", "match": {"value": kb_id}}]}

    raw_results = await qdrant_client.search_points(
        collection_name=collection,
        vector=query_embedding,
        limit=top_k * 2,  # 多取一些供重排序
        query_filter=filter_condition,
    )

    # 3. 转为 SearchResult
    results = []
    for point in raw_results:
        payload = point.payload or {}
        results.append(SearchResult(
            chunk_id=payload.get("chunk_id", point.id),
            document_id=payload.get("document_id", ""),
            document_title=payload.get("document_title", "Unknown"),
            content=payload.get("content", ""),
            score=point.score or 0.0,
            metadata={"index": payload.get("index", 0)},
        ))

    # 4. 按分数排序取 top_k
    results.sort(key=lambda r: r.score, reverse=True)

    return results[:final_top_k]


async def generate_answer(
    query: str,
    sources: List[SearchResult],
    stream: bool = False,
    temperature: float | None = None,
) -> str | AsyncGenerator[str, None]:
    """根据检索结果生成回答"""
    if not sources:
        return "未找到相关文档，无法生成回答。", 0

    # 构建上下文
    context_parts = []
    for i, src in enumerate(sources):
        context_parts.append(
            f"[来源 {i + 1}] {src.document_title}\n{src.content}"
        )
    context = "\n\n---\n\n".join(context_parts)

    system_prompt = """你是一个专业的企业知识库助手。请根据提供的参考文档回答用户问题。

要求：
1. 仅基于提供的参考文档回答，不要编造信息
2. 如果参考文档不足以回答，请明确说明
3. 回答中使用 【来源:N】 标注引用来源
4. 用中文回答
5. 回答简洁、准确、结构化"""

    user_prompt = f"""参考文档：
{context}

用户问题：{query}

请基于以上参考文档回答用户问题。"""

    temp = temperature if temperature is not None else settings.retrieval_config.get(
        "generation", {}
    ).get("temperature", 0.3)

    if stream:
        return ollama_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            temperature=temp,
        )
    else:
        answer = await ollama_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
            temperature=temp,
        )
        # 粗略估算 token 数
        tokens = len(system_prompt + user_prompt + answer) // 4
        return answer, tokens
