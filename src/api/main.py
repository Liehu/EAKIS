from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.auth import router as auth_router
from src.api.middleware.audit import AuditLoggingMiddleware
from src.api.routers.assets import router as assets_router
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.routers.inference import router as inference_router
from src.api.routers.intelligence import router as intelligence_router
from src.api.routers.interfaces import router as interfaces_router
from src.api.routers.keywords import router as keywords_router
from src.core.settings import get_settings
from src.models.database import async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 开发模式下自动建表
    settings = get_settings()
    if settings.debug:
        from src.models.database import create_tables
        await create_tables()
    yield
    # Shutdown
    await async_engine.dispose()


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    openapi_url="/v1/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Routers
app.include_router(auth_router, prefix="/v1")
app.include_router(keywords_router, prefix="/v1")
app.include_router(intelligence_router, prefix="/v1")
app.include_router(interfaces_router, prefix="/v1")
app.include_router(assets_router, prefix="/v1")
app.include_router(inference_router, prefix="/v1")


@app.get("/v1/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": settings.app_version})
