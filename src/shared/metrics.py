from prometheus_client import Counter, Histogram

TASKS_CREATED = Counter("eakis_tasks_created_total", "Total tasks created")
ASSETS_DISCOVERED = Counter("eakis_assets_discovered_total", "Total assets discovered")
VULNS_FOUND = Counter("eakis_vulns_found_total", "Total vulnerabilities found")
LLM_LATENCY = Histogram("eakis_llm_request_duration_seconds", "LLM request latency")
API_REQUEST_COUNT = Counter("eakis_api_requests_total", "Total API requests", ["method", "path", "status"])
PIPELINE_DURATION = Histogram("eakis_pipeline_duration_seconds", "Pipeline stage duration", ["stage"])
INFERENCE_REQUEST_COUNT = Counter("eakis_inference_requests_total", "Inference service requests", ["endpoint"])
RAG_UPSERT_COUNT = Counter("eakis_rag_upsert_total", "RAG documents upserted")
RAG_SEARCH_COUNT = Counter("eakis_rag_search_total", "RAG searches performed")
EXTRACTION_COUNT = Counter("eakis_extraction_total", "Pages content-extracted", ["method", "status"])
EXTRACTION_DURATION = Histogram("eakis_extraction_duration_seconds", "Content extraction latency", ["method"])
EXTRACTION_CDP_FALLBACK = Counter("eakis_extraction_cdp_fallback_total", "CDP fallback triggers")
