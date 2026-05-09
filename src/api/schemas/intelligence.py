"""Pydantic schemas for intelligence API endpoints (section 9.2 / M1)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Request schemas ---

class IntelligenceStartRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    industry: str | None = None
    domains: list[str] | None = None
    keywords: list[str] | None = None
    enabled_categories: list[str] | None = Field(default=None, description="news|official|legal|security|asset_engine")
    crawl_depth: int = Field(default=2, ge=1, le=5)


# --- Response schemas ---

class SourceStatus(BaseModel):
    source_id: str
    name: str
    category: str
    priority: int
    expected_yield: float
    status: str
    items_crawled: int = 0
    error_message: str | None = None


class DslItem(BaseModel):
    platform: str
    query: str
    valid: bool


class IntelligenceStatusResponse(BaseModel):
    task_id: UUID
    status: str
    total_sources: int = 0
    total_raw_documents: int = 0
    total_cleaned_documents: int = 0
    avg_quality_score: float = 0.0
    sources: list[SourceStatus] = Field(default_factory=list)
    dsl_queries: list[DslItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class IntelligenceDocumentItem(BaseModel):
    source_type: str
    source_name: str
    source_url: str | None = None
    content: str
    quality_score: float
    entities: list[str] = Field(default_factory=list)
    checksum: str
    published_at: str | None = None


class IntelligenceDocumentListResponse(BaseModel):
    data: list[IntelligenceDocumentItem] = Field(default_factory=list)
    pagination: dict = Field(default_factory=dict)


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0


class DslListResponse(BaseModel):
    data: list[DslItem] = Field(default_factory=list)


class SourceListResponse(BaseModel):
    data: list[SourceStatus] = Field(default_factory=list)


class IntelligenceStartResponse(BaseModel):
    task_id: UUID
    status: str
    total_sources: int = 0
    total_raw_documents: int = 0
    total_cleaned_documents: int = 0
    avg_quality_score: float = 0.0
    errors: list[str] = Field(default_factory=list)


# --- RAG search schemas ---

class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=100)
    task_id: str | None = Field(default=None, description="Filter by task ID")
    source_type: str | None = Field(default=None, description="Filter by source type")
    min_quality: float | None = Field(default=None, ge=0.0, le=1.0, description="Minimum quality score")


class RAGSearchResultItem(BaseModel):
    content: str
    score: float
    metadata: dict = Field(default_factory=dict)


class RAGSearchResponse(BaseModel):
    data: list[RAGSearchResultItem] = Field(default_factory=list)
    total: int = 0


class RAGHealthResponse(BaseModel):
    status: str
    collection: str = ""
    vector_count: int = 0
    vector_size: int = 0
    error: str | None = None
