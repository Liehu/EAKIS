import { http, HttpResponse } from 'msw';
import { mockTasks, mockTask } from './data/task';
import { mockKeywords } from './data/keyword';
import { mockAssets } from './data/asset';
import { mockInterfaces } from './data/interface';
import { mockVulnerabilities } from './data/vulnerability';
import { mockReports } from './data/report';

const TASK_ID = 'task_01J9XXXXX';

export const handlers = [
  // Tasks
  http.get('/v1/tasks', () => HttpResponse.json({
    data: mockTasks,
    pagination: { page: 1, page_size: 20, total: mockTasks.length, total_pages: 1 },
  })),
  http.get(`/v1/tasks/${TASK_ID}`, () => HttpResponse.json(mockTask)),
  http.post(`/v1/tasks/${TASK_ID}/pause`, () => HttpResponse.json({ status: 'paused' })),
  http.post(`/v1/tasks/${TASK_ID}/resume`, () => HttpResponse.json({ status: 'running' })),
  http.post(`/v1/tasks/${TASK_ID}/cancel`, () => HttpResponse.json({ status: 'cancelled' })),

  // Keywords
  http.get(`/v1/tasks/${TASK_ID}/keywords`, () => HttpResponse.json({
    data: mockKeywords,
    summary: { business_count: 46, tech_count: 29, entity_count: 38, total: 113 },
    pagination: { page: 1, page_size: 20, total: mockKeywords.length, total_pages: 1 },
  })),
  http.post(`/v1/tasks/${TASK_ID}/keywords`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ id: 'kw_new', ...body, confidence: 1.0, source: '人工添加', derived: false, used_in_dsl: false });
  }),

  // Assets
  http.get(`/v1/tasks/${TASK_ID}/assets`, () => HttpResponse.json({
    data: mockAssets,
    pagination: { page: 1, page_size: 20, total: mockAssets.length, total_pages: 1 },
  })),
  http.get(`/v1/tasks/${TASK_ID}/assets/:assetId`, ({ params }) => {
    const asset = mockAssets.find((a) => a.id === params.assetId);
    return asset ? HttpResponse.json(asset) : HttpResponse.json({ error: { code: 'NOT_FOUND', message: '资产不存在' } }, { status: 404 });
  }),

  // Interfaces
  http.get(`/v1/tasks/${TASK_ID}/interfaces`, () => HttpResponse.json({
    data: mockInterfaces,
    summary: { total: 1832, by_type: { query: 891, operation: 347, upload: 45, search: 120, auth: 89, admin: 67, other: 273 }, privilege_sensitive: 312, untested: 428 },
    pagination: { page: 1, page_size: 20, total: mockInterfaces.length, total_pages: 1 },
  })),
  http.get(`/v1/tasks/${TASK_ID}/interfaces/:interfaceId`, ({ params }) => {
    const iface = mockInterfaces.find((i) => i.id === params.interfaceId);
    return iface ? HttpResponse.json(iface) : HttpResponse.json({ error: { code: 'NOT_FOUND', message: '接口不存在' } }, { status: 404 });
  }),

  // Vulnerabilities
  http.get(`/v1/tasks/${TASK_ID}/vulnerabilities`, () => HttpResponse.json({
    data: mockVulnerabilities,
    summary: {
      by_severity: { critical: 5, high: 12, medium: 18, low: 8 },
      by_type: { PRIVILEGE_ESC: 8, SQL_INJECTION: 5, UNAUTHORIZED: 12, XSS: 6, OTHER: 12 },
      by_asset: mockAssets.slice(0, 3).map((a) => ({ asset_id: a.id, domain: a.domain, vuln_count: a.vuln_count.high + a.vuln_count.critical, max_severity: a.risk_level })),
      trend: [],
      risk_score: 8.3,
      confirmed_rate: 0.72,
    },
    pagination: { page: 1, page_size: 20, total: mockVulnerabilities.length, total_pages: 1 },
  })),
  http.get(`/v1/tasks/${TASK_ID}/vulnerabilities/:vulnId`, ({ params }) => {
    const vuln = mockVulnerabilities.find((v) => v.id === params.vulnId);
    return vuln ? HttpResponse.json(vuln) : HttpResponse.json({ error: { code: 'NOT_FOUND', message: '漏洞不存在' } }, { status: 404 });
  }),
  http.get(`/v1/tasks/${TASK_ID}/vulnerabilities/statistics`, () => HttpResponse.json({
    by_severity: { critical: 5, high: 12, medium: 18, low: 8 },
    by_type: { PRIVILEGE_ESC: 8, SQL_INJECTION: 5, UNAUTHORIZED: 12, XSS: 6, OTHER: 12 },
    by_asset: [],
    trend: [],
    risk_score: 8.3,
    confirmed_rate: 0.72,
  })),

  // Reports
  http.get(`/v1/tasks/${TASK_ID}/reports`, () => HttpResponse.json({
    data: mockReports,
    pagination: { page: 1, page_size: 20, total: mockReports.length, total_pages: 1 },
  })),
  http.get(`/v1/tasks/${TASK_ID}/reports/:reportId`, ({ params }) => {
    const report = mockReports.find((r) => r.report_id === params.reportId);
    return report ? HttpResponse.json(report) : HttpResponse.json({ error: { code: 'NOT_FOUND', message: '报告不存在' } }, { status: 404 });
  }),

  // System
  http.get('/v1/health', () => HttpResponse.json({
    status: 'healthy', version: 'v2.0.0', timestamp: new Date().toISOString(),
    components: {
      database: { status: 'healthy', latency_ms: 2 },
      redis: { status: 'healthy', latency_ms: 1 },
      qdrant: { status: 'healthy', latency_ms: 5 },
      kafka: { status: 'healthy', lag: 0 },
      llm_qwen: { status: 'healthy', latency_ms: 145 },
      llm_gpt4o: { status: 'healthy', latency_ms: 890 },
      playwright: { status: 'healthy', pool_size: 5 },
    },
  })),
  http.get('/v1/metrics', () => HttpResponse.json({
    active_tasks: 3, queued_tasks: 7, completed_tasks_today: 12, avg_task_duration_h: 6.2,
    llm_calls_today: 4821, llm_cost_usd_today: 12.47, assets_discovered_today: 1832,
    vulns_confirmed_today: 127, api_requests_per_min: 342,
  })),
  http.get('/v1/config/agents', () => HttpResponse.json({
    'KEYWORD-GEN': { model: 'qwen2.5-7b', temperature: 0.1, max_tokens: 2048, timeout_s: 30, retry_attempts: 3, enabled: true },
    'ASSET-DISCOVER': { model: 'qwen2.5-7b', temperature: 0.1, max_tokens: 2048, timeout_s: 60, retry_attempts: 3, enabled: true },
    'APICRAWL-BROWSER': { model: 'gpt-4o-mini', temperature: 0.2, max_tokens: 4096, timeout_s: 120, retry_attempts: 2, enabled: true },
    'PENTEST-AUTO': { model: 'gpt-4o', temperature: 0.3, max_tokens: 4096, timeout_s: 300, retry_attempts: 2, enabled: true },
    'REPORT-GEN': { model: 'qwen2.5-72b', temperature: 0.5, max_tokens: 8192, timeout_s: 600, retry_attempts: 1, enabled: true },
  })),
];
