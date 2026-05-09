from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+psycopg2://eakis:eakis@localhost:5432/eakis"
    database_url_async: str = "postgresql+asyncpg://eakis:eakis@localhost:5432/eakis"
    db_echo: bool = False

    # LLM (OpenAI-compatible)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str | None = None

    # Ollama (local inference)
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "igorls/gemma-4-E4B-it-heretic-GGUF:latest"
    ollama_request_timeout: float = 120.0
    ollama_num_ctx: int = 8192
    ollama_num_predict: int = 4096
    ollama_temperature: float = 0.3
    ollama_auto_detect: bool = True

    # Auth (JWT)
    jwt_secret_key: str = "eakis-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Storage (MinIO)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "eakis"
    minio_secure: bool = False

    # Cache
    cache_ttl_default: int = 300

    # Rate limit
    rate_limit_rpm: int = 60

    # App
    app_name: str = "AttackScope AI"
    app_version: str = "2.0.0"
    debug: bool = True
    cors_origins: list[str] = ["*"]

    # Qdrant / RAG
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "eakis_intel"
    qdrant_vector_size: int = 1536
    rag_embedding_model: str = "text-embedding-3-small"
    rag_use_stubs: bool = True

    # Module stubs
    intelligence_use_stubs: bool = True
    crawler_use_stubs: bool = True
    asset_discovery_use_stubs: bool = True
    asset_discovery_vector_store: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
