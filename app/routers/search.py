"""搜索和问答 API 路由"""

import json
import re
import time
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import SearchRequest, SearchResponse, QueryRequest, QueryResponse, SearchResult
from app.db.models import KnowledgeBase
from app.db.session import get_db
from app.pipeline.query import search_documents, generate_answer
from app.core.ollama_client import ollama_client
from app.core.config import settings


def _has_cjk(text: str) -> bool:
    """Check if text contains any CJK (Chinese/Japanese/Korean) characters."""
    return bool(re.search(r'[一-鿿]', text))


def normalize_text(text: str) -> str:
    """Clean tokenizer artifacts from streaming output.

    Handles:
    - Token-split word fragments ("R AG" → "RAG", "Ret rie val" → "Retrieval")
    - Missing spacing between Latin and CJK ("你好World" → "你好 World")
    - Chinese punctuation spacing
    - Redundant whitespace
    """
    if not text:
        return ""

    # 1. Normalize all whitespace to single space
    text = re.sub(r'\s+', ' ', text)

    # 2. In CJK context: remove spaces between Latin letters.
    #    Tokenizers commonly split technical terms ("R AG", "Ret rie val")
    #    and the space between Latin letters in Chinese text is always an artifact.
    if _has_cjk(text):
        text = re.sub(r'(?<=[a-zA-Z])\s+(?=[a-zA-Z])', '', text)

    # 3. Fix CJK boundary spacing: remove space between CJK and Latin
    text = re.sub(r'([一-鿿])\s+([a-zA-Z])', r'\1\2', text)
    text = re.sub(r'([a-zA-Z])\s+([一-鿿])', r'\1\2', text)

    # 4. Fix CJK-CJK spacing (token-split artifact)
    text = re.sub(r'([一-鿿])\s+([一-鿿])', r'\1\2', text)

    # 5. Insert space between Latin and CJK where missing
    #    "你好World" → "你好 World"
    text = re.sub(r'([一-鿿])([A-Za-z])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z])([一-鿿])', r'\1 \2', text)

    # 6. Normalize whitespace again after insertions
    text = re.sub(r'\s+', ' ', text)

    # 7. Fix Chinese punctuation spacing
    for k, v in {
        ' 。': '。', ' ，': '，', ' ：': '：',
        ' ！': '！', ' ？': '？', ' ；': '；',
        ' ）': '）', ' （': '（',
        ' .': '.', ' ,': ',', ' :': ':',
        ' !': '!', ' ?': '?',
    }.items():
        text = text.replace(k, v)

    return text.strip()

router = APIRouter(tags=["search"])


@router.post("/knowledge-bases/{kb_id}/search", response_model=SearchResponse)
async def search(
    kb_id: str,
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """搜索文档"""
    # 检查知识库存在
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Knowledge base not found")

    start = time.time()
    results = await search_documents(
        query=req.query,
        kb_id=kb_id,
        top_k=req.top_k,
        score_threshold=req.score_threshold,
        hybrid=req.hybrid,
    )
    elapsed = (time.time() - start) * 1000

    return SearchResponse(
        results=results,
        total=len(results),
        query_time_ms=round(elapsed, 2),
    )


@router.post("/knowledge-bases/{kb_id}/query", response_model=QueryResponse)
async def query(
    kb_id: str,
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """问答（非流式）"""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Knowledge base not found")

    start = time.time()

    # 1. 搜索相关文档
    sources = await search_documents(
        query=req.query,
        kb_id=kb_id,
        top_k=req.top_k,
        hybrid=True,
    )

    # 2. 生成回答
    answer, tokens = await generate_answer(
        query=req.query,
        sources=sources,
        stream=False,
        temperature=req.temperature,
    )

    elapsed = (time.time() - start) * 1000

    return QueryResponse(
        answer=answer,
        sources=sources,
        tokens_used=tokens,
        query_time_ms=round(elapsed, 2),
    )


@router.post("/knowledge-bases/{kb_id}/query/stream")
async def query_stream(
    kb_id: str,
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """流式问答（SSE）"""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Knowledge base not found")

    sources = await search_documents(
        query=req.query,
        kb_id=kb_id,
        top_k=req.top_k,
        hybrid=True,
    )

    async def event_generator():
        # 先发送来源
        sources_data = [
            {
                "index": i,
                "chunk_index": s.chunk_index,
                "title": s.document_title,
                "document_id": s.document_id,
                "chunk_id": s.chunk_id,
                "content": s.content[:200],
                "score": s.score,
                "updated_at": s.updated_at,
            }
            for i, s in enumerate(sources)
        ]
        yield {"event": "sources", "data": json.dumps(sources_data, ensure_ascii=False)}

        if not sources:
            yield {"event": "token", "data": "未找到相关文档，无法生成回答。"}
            yield {"event": "done", "data": ""}
            return

        # 构建 prompt（复用 generate_answer 的逻辑）
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

用户问题：{req.query}

请基于以上参考文档回答用户问题。"""

        temp = req.temperature if req.temperature is not None else settings.retrieval_config.get(
            "generation", {}
        ).get("temperature", 0.3)

        chat_gen = await ollama_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            temperature=temp,
        )

        # 后端流式聚合：缓冲 token，句子级推送
        buf = ""
        SENTENCE_END = re.compile(r'[。！？.!?\n]')
        MIN_FLUSH = 50         # 最小推送字符数
        MAX_FLUSH = 120        # 强制推送阈值，避免前端等太久

        async for chunk in chat_gen:
            if not chunk:
                continue
            buf += chunk

            # 强制推送：buffer 超过最大阈值
            if len(buf) >= MAX_FLUSH:
                yield {"event": "token", "data": normalize_text(buf)}
                buf = ""
            # 正常推送：达到最小字符数，且在句子边界
            elif len(buf) >= MIN_FLUSH and SENTENCE_END.search(buf):
                # 找到最后一个句子结束符，按此分割
                match_iter = list(SENTENCE_END.finditer(buf))
                if match_iter:
                    last_end = match_iter[-1]
                    split_at = last_end.end()
                    flush_part = buf[:split_at]
                    buf = buf[split_at:]
                    yield {"event": "token", "data": normalize_text(flush_part)}

        if buf:
            yield {"event": "token", "data": normalize_text(buf)}

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
