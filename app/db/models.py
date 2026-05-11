"""SQLAlchemy 数据库模型"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Integer, DateTime, JSON, ForeignKey,
    Boolean, Float, Enum as SAEnum,
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(AsyncAttrs, DeclarativeBase):
    pass


def _uuid():
    return str(uuid.uuid4())


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    document_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    permissions = relationship("KnowledgeBasePermission", back_populates="knowledge_base", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=_uuid)
    kb_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    title = Column(String(512), nullable=False)
    content_type = Column(String(128), default="text/markdown")
    file_path = Column(String(1024))
    file_size = Column(Integer, default=0)
    status = Column(SAEnum(DocumentStatus), default=DocumentStatus.PENDING)
    source_info = Column(JSON, default=dict)
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    meta_info = Column("metadata", JSON, default=dict)
    embedding_id = Column(String, nullable=True)  # Qdrant point ID
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


# ============ Auth 模型 ============

class Role(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    username = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(Role), default=Role.VIEWER, nullable=False)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    display_name = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = relationship("Department", back_populates="users")


class Department(Base):
    __tablename__ = "departments"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="department")


class KnowledgeBasePermission(Base):
    """知识库权限：用户可以访问哪些知识库"""
    __tablename__ = "kb_permissions"

    id = Column(String, primary_key=True, default=_uuid)
    kb_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    permission = Column(String(32), default="viewer")  # admin / editor / viewer

    knowledge_base = relationship("KnowledgeBase", back_populates="permissions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_uuid)
    event_type = Column(String(64), nullable=False)  # query / ingest / login / config_change
    user_id = Column(String(128), nullable=True)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(128), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
