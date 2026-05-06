"""Database connection and Base for SQLAlchemy models.
Provides `engine`, `SessionLocal` and declarative `Base`.
Primary target: PostgreSQL 16 (production).
Fallback: SQLite (local development).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://eakis:eakis@localhost:5432/eakis")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def is_postgresql() -> bool:
    return engine.dialect.name == "postgresql"
