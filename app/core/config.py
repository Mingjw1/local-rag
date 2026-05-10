"""配置管理 — 从 YAML 文件和环境变量加载配置"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用
    app_name: str = "Local RAG KB"
    debug: bool = False
    log_level: str = "info"
    cors_origins: str = "*"
    secret_key: str = "change_me"

    # 数据库
    database_url: str = "postgresql+asyncpg://ragkb:ragkb_secret@localhost:5432/ragkb"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: Optional[str] = None

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minio_secret"
    minio_bucket: str = "ragkb-docs"
    minio_secure: bool = False

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_generation_model: str = "qwen2.5:7b"

    # Paths
    config_dir: str = str(Path(__file__).parent.parent.parent / "config")
    data_dir: str = str(Path(__file__).parent.parent.parent / "data")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def rag_config(self) -> dict:
        """加载 rag-controller.yaml"""
        path = Path(self.config_dir) / "rag-controller.yaml"
        with open(path) as f:
            return _resolve_env(yaml.safe_load(f))

    @property
    def models_config(self) -> dict:
        """加载 models.yaml"""
        path = Path(self.config_dir) / "models.yaml"
        with open(path) as f:
            return yaml.safe_load(f)

    @property
    def retrieval_config(self) -> dict:
        """加载 retrieval.yaml"""
        path = Path(self.config_dir) / "retrieval.yaml"
        with open(path) as f:
            return yaml.safe_load(f)


def _resolve_env(obj):
    """递归替换配置中的 ${VAR} 为环境变量值"""
    if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        env_var = obj[2:-1]
        default = None
        if ":-" in env_var:
            env_var, default = env_var.split(":-", 1)
        return os.environ.get(env_var, default or "")
    if isinstance(obj, dict):
        return {k: _resolve_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env(v) for v in obj]
    return obj


settings = Settings()
