# Intelligence Collection Module (M1) Design

## Overview

Implement the M1 Intelligence Collection Module based on `docs/extract/03_情报采集模块.md` and `docs/extract/09_API 设计规范.md`. The module collects OSINT data from multiple sources, cleans it, and stores structured intelligence for downstream keyword generation.

Architecture: **Service-oriented with abstract interfaces (Approach A)**. Each agent owns a clear responsibility and depends on abstract service interfaces. Stubs ship as default implementations, swappable via config.

## Module Structure

```
src/intelligence/
├── __init__.py                  # Exports IntelligenceModule
├── module.py                    # Main orchestration class
├── agents/
│   ├── __init__.py
│   ├── datasource.py            # DataSourceAgent
│   ├── dsl.py                   # DSLAgent (config-driven)
│   ├── crawler.py               # CrawlerAgent
│   └── cleaner.py               # CleanerAgent
├── services/
│   ├── __init__.py
│   ├── base.py                  # Abstract interfaces
│   ├── rag_client.py            # RAG client (abstract + Qdrant impl)
│   ├── llm_client.py            # LLM client (abstract + OpenAI impl)
│   ├── generic_scraper.py       # Generic engine scraper (config-driven)
│   └── scrapers/
│       ├── __init__.py
│       ├── base_scraper.py      # Abstract scraper base class
│       ├── news_scraper.py      # News scraper (Stub)
│       ├── official_scraper.py  # Official site scraper (Stub)
│       └── legal_scraper.py     # ICP/business scraper (Stub)
├── engine_specs/
│   ├── __init__.py
│   └── engines.yaml             # Engine field docs + search URLs + operators
├── models.py                    # Pydantic internal data models
└── config.py                    # IntelligenceConfig
```

## Data Flow

```
Task Input → DataSourceAgent → CrawlerAgent → CleanerAgent → DB + RAG
                 ↓                                  ↑
            DSLAgent ──→ DSL queries ──→ used by crawler
                 ↑
        engine_specs.yaml (field docs + URLs + operators)
```

## Engine Spec Configuration

All search engine specifications are defined in `engine_specs/engines.yaml` as structured data. DSLAgent reads these specs and passes them to the LLM, which dynamically assembles DSL queries. The generic scraper uses the same specs to construct API calls.

**No per-engine wrapper code required.** Adding a new engine only requires adding a YAML entry.

```yaml
engines:
  fofa:
    display_name: "Fofa"
    search_url: "https://fofa.info/api/v1/search/all"
    auth_type: "email+apikey"
    fields:
      domain: 'domain="{value}"'
      title: 'title="{value}"'
      header: 'header="{value}"'
      cert: 'cert="{value}"'
      icon_hash: 'icon_hash="{value}"'
    operators: ["&&", "||", "()"]
    pagination: { param: "page", size_param: "size", default_size: 100 }
    response_path: "results"

  hunter:
    display_name: "Hunter"
    search_url: "https://hunter.qianxin.com/openApi/search"
    auth_type: "apikey"
    fields:
      domain.suffix: 'domain.suffix="{value}"'
      web.title: 'web.title="{value}"'
      ip: 'ip="{value}"'
    operators: ["&&", "||", "()"]
    pagination: { param: "page", size_param: "page_size", default_size: 100 }
    response_path: "data.arr"

  shodan:
    display_name: "Shodan"
    search_url: "https://api.shodan.io/shodan/host/search"
    auth_type: "apikey"
    fields:
      org: 'org:"{value}"'
      http.title: 'http.title:"{value}"'
      port: 'port:{value}'
      ssl.cert.subject.cn: 'ssl.cert.subject.cn:"{value}"'
    operators: [" ", "+"]
    pagination: { param: "page", default_size: 100 }
    response_path: "matches"
```

## Agent Responsibilities

### DataSourceAgent
- **Input**: company name, industry, config
- **Output**: `list[DataSource]` with priority, expected yield, rate limit
- **Logic**: Query RAG for historical effective sources → match by company scale/industry → priority sort

### DSLAgent (Config-Driven)
- **Input**: keyword list + target platforms
- **Output**: `list[DslQuery]` per platform
- **Logic**:
  1. Load engine specs from `engines.yaml`
  2. Build prompt with keywords + engine field docs + operators
  3. LLM assembles DSL for each platform
  4. Validate generated DSL against engine field patterns
- **Fallback**: If LLM fails, concatenate primary keyword into each engine's first field template

### CrawlerAgent
- **Input**: data source list + DSL map
- **Output**: `list[RawDocument]`
- **Logic**: Batch concurrent crawl by priority → anti-crawl (UA rotation, delay, proxy) → publish `osint.crawl.complete` event
- **Asset engine sources**: Use `GenericEngineScraper` which reads engine specs to construct API calls (URL + params + auth). No per-engine code.
- **Non-engine sources** (news/official/legal): Use category-specific stub scrapers
- **Error handling**: Single source failure does not block others; partial failure recorded

### CleanerAgent
- **Input**: raw document list
- **Output**: `list[CleanedDocument]` → write to IntelDocument table + RAG
- **Logic**: Deduplicate (MinHash/SHA256) → HTML strip → quality score → entity pre-recognition → incremental RAG upsert

### IntelligenceModule (orchestrator)

```python
async def run(self, task_id, company_name, config):
    sources = await self.datasource_agent.select_sources(company_info, config)
    dsl_map = await self.dsl_agent.generate(keywords, platforms)
    raw_docs = await self.crawler_agent.crawl(sources, dsl_map, config)
    cleaned = await self.cleaner_agent.clean(raw_docs, task_id)
    return CollectionResult(...)
```

## Abstract Service Interfaces

| Interface | Method | Purpose |
|-----------|--------|---------|
| `BaseScraper` | `async scrape(query, config) -> list[RawDocument]` | Single source crawl |
| `BaseLLMClient` | `async generate(prompt, **kwargs) -> str` | LLM inference |
| `BaseRAGClient` | `async upsert(docs) / async search(query, top_k) -> list[RAGResult]` | Vector search |

`GenericEngineScraper` implements `BaseScraper` and reads engine specs to handle any configured engine. No per-engine subclasses.

## API Routes

File: `src/api/routers/intelligence.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/tasks/{task_id}/intelligence` | POST | Start intelligence collection |
| `/v1/tasks/{task_id}/intelligence` | GET | Get collection status & progress |
| `/v1/tasks/{task_id}/intelligence/documents` | GET | Paginated cleaned document list |
| `/v1/tasks/{task_id}/intelligence/documents/{doc_id}` | GET | Single document detail |
| `/v1/tasks/{task_id}/intelligence/dsl` | GET | Generated DSL queries |
| `/v1/tasks/{task_id}/intelligence/sources` | GET | Source selection results & status |

Pagination follows API spec format: `{data, pagination: {page, page_size, total, total_pages}}`.
Errors follow: `{error: {code, message, details, request_id, timestamp}}`.

Integration: Register router in `src/api/main.py` under `/v1` prefix.

## Error Handling

- **External service failure**: Wrapped in `CircuitBreaker`, logs to `AgentLog` table
- **Crawler task-level errors**: Single source failure → others continue; status = `partial_failure`
- **LLM failure**: DSL generation degrades to template-based fallback using engine spec field definitions
- All exceptions caught as `EAKISBaseError` subclasses, API layer converts to standard error response

## Logging

- `get_logger("intelligence.{agent_name}")` from `src/shared/logger.py`
- Key milestones written to `AgentLog`: source selection done, crawl batch done, clean batch done
- Events published via `EventBus`: `osint.crawl.complete`, `osint.clean.batch`

## Testing

| Level | Content | Location |
|-------|---------|----------|
| Unit | 4 agents core logic with mock services | `tests/unit/intelligence/` |
| Integration | End-to-end flow with stubs + SQLite | `tests/intelligence/` |
| API | Route endpoint validation (TestClient) | `tests/unit/api/test_intelligence_router.py` |

Target: ≥ 75% coverage, aligned with progress table requirements.
