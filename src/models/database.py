"""Database connection and Base for SQLAlchemy models.
Provides sync + async engines, session factories, and declarative Base.
Primary target: PostgreSQL 16 (production).
Fallback: SQLite (local development).
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.settings import get_settings

settings = get_settings()

# ---- Sync engine (Alembic / legacy) ----
_sync_url = settings.database_url
engine = create_engine(
    _sync_url,
    connect_args={"check_same_thread": False} if _sync_url.startswith("sqlite") else {},
    pool_pre_ping=True,
    future=True,
    echo=settings.db_echo,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# ---- Async engine (FastAPI runtime) ----
_async_url = settings.database_url_async
async_engine = create_async_engine(
    _async_url,
    connect_args={"check_same_thread": False} if "sqlite" in _async_url else {},
    pool_pre_ping=True,
    echo=settings.db_echo,
)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False,
)

Base = declarative_base()


def is_postgresql() -> bool:
    return engine.dialect.name == "postgresql"


async def create_tables() -> None:
    """Create all tables — used in dev mode when Alembic is not set up."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
