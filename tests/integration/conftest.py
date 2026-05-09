"""Integration test fixtures."""

import logging
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.main import app
from src.models.database import Base
from src.api.middleware.rate_limit import RateLimitMiddleware


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Set a very high RPM so batch tests don't hit rate limits."""
    for mw in app.user_middleware:
        if mw.cls is RateLimitMiddleware:
            original_kwargs = mw.kwargs.copy()
            mw.kwargs["rpm"] = 9999
            yield
            mw.kwargs.update(original_kwargs)
            return
    yield


class LogCapture(logging.Handler):
    """Captures log records for assertion."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture()
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def async_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture()
def random_task_id() -> str:
    return str(uuid4())


@pytest.fixture()
def log_capture():
    """Attach a LogCapture handler to the 'eakis.audit' logger."""
    logger = logging.getLogger("eakis.audit")
    handler = LogCapture()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield handler
    logger.removeHandler(handler)
