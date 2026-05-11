"""FastAPI 主应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.core.config import settings
from app.db.session import init_db, async_session
from app.routers import documents, search, admin, wiki, auth
from app.routers.auth import hash_password
from app.db.models import User, Role
from app.core.ollama_client import ollama_client


async def _bootstrap_admin():
    """启动时自动创建默认 admin 用户（如果不存在）"""
    async with async_session() as db:
        result = await db.execute(select(User).where(User.role == Role.ADMIN))
        if not result.scalar_one_or_none():
            admin_user = User(
                username="admin",
                email="admin@local-rag.local",
                password_hash=hash_password("admin123"),
                display_name="Admin",
                role=Role.ADMIN,
            )
            db.add(admin_user)
            await db.commit()
            print("✓ 默认管理员已创建 (admin / admin123)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：初始化数据库、检查 Ollama、创建默认管理员
    await init_db()
    await _bootstrap_admin()
    ollama_ok = await ollama_client.check_health()
    if ollama_ok:
        print("✓ Ollama 服务连接成功")
    else:
        print("⚠ Ollama 服务未响应，请确保 Ollama 已启动")
    yield
    # 关闭时：清理资源
    await ollama_client.close()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(wiki.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}
