"""文档管理 API 路由"""

import os
import uuid
import hashlib
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.models import DocumentResponse, KnowledgeBaseCreate, KnowledgeBaseResponse
from app.db.models import Document, Chunk, KnowledgeBase, DocumentStatus
from app.db.session import get_db
from app.pipeline.ingest import process_document

router = APIRouter(tags=["documents"])


# === 知识库 CRUD ===

@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    req: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
):
    kb = KnowledgeBase(id=str(uuid.uuid4()), name=req.name, description=req.description)
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return kb


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
    return result.scalars().all()


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")
    return kb


@router.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")
    await db.delete(kb)
    await db.commit()
    return {"status": "deleted"}


# === 文档 CRUD ===

@router.post("/knowledge-bases/{kb_id}/documents", response_model=DocumentResponse)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    title: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """上传并导入文档"""
    # 检查知识库存在
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    # 保存上传的文件
    upload_dir = Path(settings.data_dir) / "raw" / kb_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()[:16]
    safe_filename = f"{file_hash}_{file.filename}"
    file_path = upload_dir / safe_filename
    with open(file_path, "wb") as f:
        f.write(content)

    # 创建文档记录
    doc = Document(
        id=str(uuid.uuid4()),
        kb_id=kb_id,
        title=title or file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        file_path=str(file_path),
        file_size=len(content),
        status=DocumentStatus.PENDING,
        source_info={"filename": file.filename, "hash": file_hash},
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 异步处理文档（简化：同步处理）
    try:
        await process_document(doc.id, db)
    except Exception as e:
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)
        await db.commit()

    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        content_type=doc.content_type,
        status=doc.status.value,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[DocumentResponse])
async def list_documents(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.kb_id == kb_id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=d.id, title=d.title, content_type=d.content_type,
            status=d.status.value, chunk_count=d.chunk_count,
            created_at=d.created_at, updated_at=d.updated_at,
        )
        for d in docs
    ]


@router.get("/knowledge-bases/{kb_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(kb_id: str, doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.kb_id == kb_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return DocumentResponse(
        id=doc.id, title=doc.title, content_type=doc.content_type,
        status=doc.status.value, chunk_count=doc.chunk_count,
        created_at=doc.created_at, updated_at=doc.updated_at,
    )


@router.delete("/knowledge-bases/{kb_id}/documents/{doc_id}")
async def delete_document(kb_id: str, doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.kb_id == kb_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    # 删除文件
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    await db.delete(doc)
    await db.commit()
    return {"status": "deleted"}


@router.post("/knowledge-bases/{kb_id}/documents/{doc_id}/reindex")
async def reindex_document(kb_id: str, doc_id: str, db: AsyncSession = Depends(get_db)):
    """重新索引文档"""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.kb_id == kb_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # 删除旧的 chunks
    await db.execute(delete(Chunk).where(Chunk.document_id == doc_id))
    doc.status = DocumentStatus.PENDING
    doc.chunk_count = 0
    await db.commit()

    # 重新处理
    try:
        await process_document(doc.id, db)
    except Exception as e:
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)
        await db.commit()
        raise HTTPException(500, str(e))

    return {"status": "reindexed", "chunk_count": doc.chunk_count}
