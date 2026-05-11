"""文档导入流水线：解析 → 分块 → Embedding → 存储 → Wiki 更新"""

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.models import DocumentChunk
from app.db.models import Document, Chunk, DocumentStatus
from app.db.session import async_session
from app.pipeline.chunking import chunk_document
from app.pipeline.embedding import generate_embeddings
from app.pipeline.parsers import parse_document
from app.wiki.engine import WikiEngine
from app.db.qdrant import qdrant_client


async def process_document(doc_id: str, db: AsyncSession):
    """处理单个文档：解析 → 分块 → Embedding → 存储"""
    # 确保 Qdrant collection 存在
    collection = settings.rag_config["vector_db"]["collection_name"]
    embed_model = settings.models_config["models"]["embedding"]["options"][settings.ollama_embedding_model]
    await qdrant_client.ensure_collection(collection, embed_model["dim"])

    # 获取文档
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Document {doc_id} not found")

    doc.status = DocumentStatus.PROCESSING
    await db.commit()

    try:
        # 1. 解析文档内容
        content = parse_document(doc.file_path, doc.content_type)
        if not content:
            raise ValueError(f"Failed to parse document: {doc.file_path}")

        # 2. 分块
        chunks_text = chunk_document(content, doc.content_type)

        # 3. 生成 Embedding
        embeddings = await generate_embeddings(chunks_text)

        # 4. 存储到 Qdrant + PostgreSQL
        chunk_records = []
        qdrant_points = []

        for i, (text, emb) in enumerate(zip(chunks_text, embeddings)):
            chunk_id = str(uuid.uuid4())
            chunk_records.append(Chunk(
                id=chunk_id,
                document_id=doc_id,
                index=i,
                content=text,
                meta_info={
                    "document_id": doc_id,
                    "document_title": doc.title,
                    "chunk_index": i,
                    "total_chunks": len(chunks_text),
                },
            ))
            qdrant_points.append({
                "id": chunk_id,
                "vector": emb,
                "payload": {
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "document_title": doc.title,
                    "kb_id": doc.kb_id,
                    "index": i,
                    "content": text[:500],  # payload 中存摘要
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                },
            })

        # 批量写入 PostgreSQL
        db.add_all(chunk_records)
        doc.status = DocumentStatus.READY
        doc.chunk_count = len(chunks_text)
        await db.commit()

        # 批量写入 Qdrant
        if qdrant_points:
            await qdrant_client.upsert_points(
                collection_name=settings.rag_config["vector_db"]["collection_name"],
                points=qdrant_points,
            )

        # 5. 更新知识库统计
        from app.db.models import KnowledgeBase
        kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == doc.kb_id))
        kb = kb_result.scalar_one_or_none()
        if kb:
            kb.document_count = (kb.document_count or 0) + 1
            kb.chunk_count = (kb.chunk_count or 0) + len(chunks_text)
            await db.commit()

        # 6. 更新 Wiki
        wiki = WikiEngine(doc.kb_id)
        await wiki.after_ingest(doc, chunks_text)

    except Exception as e:
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)
        await db.commit()
        raise
