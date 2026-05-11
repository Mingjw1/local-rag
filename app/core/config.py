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
    secret_key: str = "change_me_in_production"

    # 数据库
    database_url: str = "postgresql+asyncpg://ragkb:ragkb_secret@localhost:5432/ragkb"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: Optional[str] = None

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None

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

    # 云端 LLM
    deepseek_api_key: Optional[str] = None
    deepseek_api_base: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    openai_api_key: Optional[str] = None
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    claude_api_key: Optional[str] = None
    claude_api_base: str = "https://api.anthropic.com"
    claude_model: str = "claude-sonnet-4-20250514"

    # Embedding & Rerank
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768
    rerank_model: Optional[str] = None
    rerank_enabled: bool = False

    # 检索参数
    chunk_size: int = 512
    chunk_overlap: int = 64
    chunk_strategy: str = "recursive"
    top_k: int = 5
    rerank_top_k: int = 5
    search_score_threshold: float = 0.0
    hybrid_search_enabled: bool = True
    hybrid_dense_weight: float = 0.7
    hybrid_sparse_weight: float = 0.3

    # 生成参数
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048
    llm_context_window: int = 8000

    # Paths
    config_dir: str = str(Path(__file__).parent.parent.parent / "config")
    data_dir: str = str(Path(__file__).parent.parent.parent / "data")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def llm_provider(self) -> str:
        """自动选择可用的 LLM 提供方（优先级: DeepSeek > OpenAI > Claude > Ollama）"""
        if self.deepseek_api_key:
            return "deepseek"
        if self.openai_api_key:
            return "openai"
        if self.claude_api_key:
            return "claude"
        return "ollama"

    @property
    def rag_config(self) -> dict:
        """加载 rag-controller.yaml"""
        path = Path(self.config_dir) / "rag-controller.yaml"
        with open(path) as f:
            return _resolve_env(yaml.safe_load(f))

    @property
    def models_config(self) -> dict:
        """加载 models.yaml 并用 env 覆盖"""
        path = Path(self.config_dir) / "models.yaml"
        with open(path) as f:
            return _resolve_env(yaml.safe_load(f))

    @property
    def retrieval_config(self) -> dict:
        """加载 retrieval.yaml 并用 env 覆盖"""
        path = Path(self.config_dir) / "retrieval.yaml"
        with open(path) as f:
            return _resolve_env(yaml.safe_load(f))


def _resolve_env(obj):
    """递归替换配置中的 ${VAR} 为环境变量值，自动转换类型"""
    if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        env_var = obj[2:-1]
        default = None
        if ":-" in env_var:
            env_var, default = env_var.split(":-", 1)
        val = os.environ.get(env_var)
        if val is None:
            val = default or ""
        # 类型转换：布尔值
        if val.lower() in ("true",):
            return True
        if val.lower() in ("false",):
            return False
        # 类型转换：整数
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
        # 类型转换：浮点数
        try:
            return float(val)
        except (ValueError, TypeError):
            pass
        return val
    if isinstance(obj, dict):
        return {k: _resolve_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env(v) for v in obj]
    return obj


settings = Settings()
