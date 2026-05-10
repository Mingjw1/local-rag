"""管理 API 路由"""

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.ollama_client import ollama_client

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def health():
    """系统健康检查"""
    ollama_ok = await ollama_client.check_health()
    return {
        "status": "ok" if ollama_ok else "degraded",
        "ollama": "connected" if ollama_ok else "unavailable",
    }


@router.get("/models")
async def list_models():
    """列出已配置的模型"""
    return settings.models_config


@router.post("/reload-config")
async def reload_config():
    """触发热加载配置"""
    from app.core.config import settings as s
    # Force re-read from env
    s.__init__()
    return {"status": "config reloaded"}
