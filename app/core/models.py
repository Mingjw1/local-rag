"""Pydantic 数据模型"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# === 文档 ===
class DocumentCreate(BaseModel):
    title: str
    content_type: str = "text/markdown"
    metadata: dict = {}


class DocumentResponse(BaseModel):
    id: str
    title: str
    content_type: str
    status: str  # pending / processing / ready / failed
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentChunk(BaseModel):
    id: str
    document_id: str
    index: int
    content: str
    metadata: dict = {}
    embedding: Optional[list[float]] = None


# === 搜索 ===
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    score_threshold: Optional[float] = None
    hybrid: bool = True


class SearchResult(BaseModel):
    chunk_id: str
    chunk_index: int = 0
    document_id: str
    document_title: str
    content: str
    score: float
    updated_at: Optional[str] = None
    metadata: dict = {}


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query_time_ms: float


# === 问答 ===
class QueryRequest(BaseModel):
    query: str
    stream: bool = False
    top_k: int = 5
    temperature: Optional[float] = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SearchResult] = []
    tokens_used: int = 0
    query_time_ms: float


# === 知识库 ===
class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str = ""


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime
