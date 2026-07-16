from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.auth import router as auth_router
from src.api.middleware.audit import AuditLoggingMiddleware
from src.api.routers.assets import router as assets_router
from src.api.routers.audit_logs import router as audit_logs_router
from src.api.routers.companies import router as companies_router
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.routers.inference import router as inference_router
from src.api.routers.intelligence import router as intelligence_router
from src.api.routers.interfaces import router as interfaces_router
from src.api.routers.keywords import router as keywords_router
from src.api.routers.knowledge import router as knowledge_router
from src.api.routers.tasks import router as tasks_router
from src.api.routers.templates import router as templates_router
from src.api.routers.teams import router as teams_router
from src.api.routers.tools import router as tools_router
from src.api.routers.users import router as users_router
from src.api.routers.vulnerabilities import router as vulnerabilities_router
from src.api.routers.reports import router as reports_router
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
app.include_router(tasks_router, prefix="/v1")
app.include_router(keywords_router, prefix="/v1")
app.include_router(intelligence_router, prefix="/v1")
app.include_router(interfaces_router, prefix="/v1")
app.include_router(assets_router, prefix="/v1")
app.include_router(inference_router, prefix="/v1")
app.include_router(users_router, prefix="/v1")
app.include_router(teams_router, prefix="/v1")
app.include_router(audit_logs_router, prefix="/v1")
app.include_router(vulnerabilities_router, prefix="/v1")
app.include_router(reports_router, prefix="/v1")
app.include_router(companies_router, prefix="/v1")
app.include_router(knowledge_router, prefix="/v1")
app.include_router(templates_router, prefix="/v1")
app.include_router(tools_router, prefix="/v1")


@app.get("/v1/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": settings.app_version})
