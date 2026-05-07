from prometheus_client import Counter, Histogram

TASKS_CREATED = Counter("eakis_tasks_created_total", "Total tasks created")
ASSETS_DISCOVERED = Counter("eakis_assets_discovered_total", "Total assets discovered")
VULNS_FOUND = Counter("eakis_vulns_found_total", "Total vulnerabilities found")
LLM_LATENCY = Histogram("eakis_llm_request_duration_seconds", "LLM request latency")
API_REQUEST_COUNT = Counter("eakis_api_requests_total", "Total API requests", ["method", "path", "status"])
PIPELINE_DURATION = Histogram("eakis_pipeline_duration_seconds", "Pipeline stage duration", ["stage"])
