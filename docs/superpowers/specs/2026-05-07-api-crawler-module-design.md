# M4 智能接口爬取模块 — Design Spec

## Overview

Implement the M4 API Crawler module that discovers and catalogs HTTP interfaces from target assets through 4 crawl layers: static analysis, dynamic browser interaction, CDP traffic capture, and similar-interface inference. Follows M1/M2 patterns with stub services for external dependencies.

## Architecture

Agent-per-layer pattern, orchestrated by `ApiCrawlerModule`:

```
Assets → StaticAnalyzer → BrowserAgent → CDPInterceptor → Classifier → VersionTracker → Interfaces[]
```

## File Structure

```
src/api_crawler/
├── __init__.py
├── module.py                    # ApiCrawlerModule orchestration
├── config.py                    # CrawlerConfig dataclasses
├── models.py                    # Internal data models
├── agents/
│   ├── __init__.py
│   ├── static_analyzer.py       # Layer 1: real regex-based JS/HTML/Swagger/GraphQL
│   ├── browser_agent.py         # Layer 2: stub LLM browser control
│   ├── cdp_interceptor.py       # Layer 3: stub CDP traffic capture
│   ├── interface_classifier.py  # Classification + normalization (real)
│   └── version_tracker.py       # Checksum diff version tracking (real)
├── services/
│   ├── __init__.py
│   ├── base.py                  # BaseBrowserClient, BaseCDPClient abstractions
│   └── stub_browser.py          # Stub implementations
src/api/routers/interfaces.py    # REST endpoints (section 9.5)
src/api/schemas/interface.py     # Pydantic request/response models
tests/unit/api_crawler/          # Unit tests
```

## Components

### 1. Config (`config.py`)

```python
@dataclass
class StaticAnalysisConfig:
    max_js_files: int = 50
    max_html_pages: int = 100
    enable_sourcemap: bool = True

@dataclass
class BrowserConfig:
    headless: bool = True
    timeout_s: float = 30.0
    max_interactions: int = 20

@dataclass
class CDPConfig:
    max_buffer_mb: int = 50
    capture_ws: bool = True
    capture_sse: bool = True

@dataclass
class CrawlerConfig:
    static: StaticAnalysisConfig = field(default_factory=StaticAnalysisConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    cdp: CDPConfig = field(default_factory=CDPConfig)
    use_stubs: bool = True
```

### 2. Models (`models.py`)

- `CapturedRequest` — raw captured HTTP request (url, method, headers, body, type)
- `StaticInterface` — interface extracted from static analysis (path, method, params, source)
- `ClassifiedInterface` — classified + normalized interface ready for storage
- `CrawlStatus` — enum: PENDING, ANALYZING, CRAWLING, CLASSIFYING, COMPLETED, FAILED
- `CrawlResult` — summary with counts per layer and per type

### 3. Agents

**StaticAnalyzer (real logic):**
- Regex patterns for API paths, fetch/axios calls, Vue/React router paths, Swagger URLs, GraphQL endpoints
- HTML form action extraction
- Returns list of `StaticInterface`

**BrowserAgent (stub):**
- Accepts URL + already-captured interfaces
- Returns simulated `CapturedRequest` list representing dynamic interaction discoveries

**CDPInterceptor (stub):**
- Accepts URL
- Returns simulated WebSocket/SSE/gRPC captures

**InterfaceClassifier (real logic):**
- Rule-based classification using path/method heuristics
- Maps to types: auth, query, operation, upload, search, webhook, config, admin
- Detects privilege-sensitive parameters (userId, roleId, tenantId, orgId, etc.)
- Normalizes path patterns (replace IDs with placeholders)
- Assigns test_priority 1-10

**VersionTracker (real logic):**
- SHA-256 checksum of path+method+parameters
- Detects changes between crawl runs
- Increments version on change

### 4. Module (`module.py`)

`ApiCrawlerModule` mirrors `IntelligenceModule`:
- Constructor takes config + service dependencies
- `run()` orchestrates full pipeline: static → browser → CDP → classify → version-track
- `get_status()` returns current crawl status
- `get_interfaces()` returns paginated, filtered interfaces
- `get_interface()` returns single interface detail
- `update_interface()` allows manual priority/notes changes

### 5. API Router (`interfaces.py`)

Per section 9.5:
- `POST /v1/tasks/{task_id}/interfaces/crawl` — trigger crawl for assets
- `GET /v1/tasks/{task_id}/interfaces` — list with filters (asset_id, type, privilege_sensitive, auth_required, min_priority, method) + pagination
- `GET /v1/tasks/{task_id}/interfaces/{interface_id}` — detail
- `PATCH /v1/tasks/{task_id}/interfaces/{interface_id}` — update priority/notes/skip_test

### 6. Schemas (`interface.py`)

Request/response Pydantic models matching section 9.5 JSON shapes.

### 7. Tests

Unit tests covering:
- StaticAnalyzer regex patterns
- InterfaceClassifier classification rules
- VersionTracker checksum diff
- Module orchestration pipeline
- API router endpoints
- Edge cases (empty assets, no interfaces found, duplicates)

## Real vs Stub

| Component | Implementation | Logic |
|-----------|---------------|-------|
| StaticAnalyzer | Real | Regex parsing, path extraction |
| BrowserAgent | Stub | Simulated captured requests |
| CDPInterceptor | Stub | Simulated WS/SSE captures |
| InterfaceClassifier | Real | Rule-based type detection |
| VersionTracker | Real | Checksum-based diffing |
| Services | Stub | BaseBrowserClient, BaseCDPClient |

## Dependencies

No new dependencies beyond existing pyproject.toml (already has Playwright, Pydantic, FastAPI, SQLAlchemy).
