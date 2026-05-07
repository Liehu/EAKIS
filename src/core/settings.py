from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+psycopg2://eakis:eakis@localhost:5432/eakis"
    database_url_async: str = "postgresql+asyncpg://eakis:eakis@localhost:5432/eakis"
    db_echo: bool = False

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str | None = None

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

    # Module stubs
    intelligence_use_stubs: bool = True
    crawler_use_stubs: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
