import { http, HttpResponse } from 'msw';
import { mockTasks, mockTask } from './data/task';
import { mockKeywords } from './data/keyword';
import { mockAssets, mockIPAssets, mockDomainAssets, mockWebAssets, mockAppAssets, mockMiniProgramAssets } from './data/asset';
import { mockInterfaces } from './data/interface';
import { mockVulnerabilities } from './data/vulnerability';
import { mockReports } from './data/report';
import { mockProviders, mockModelAllocations, mockProviderUsage } from './data/provider';
import { mockCompanies, mockCompanyDetails, mockSubCompanies } from './data/company';
import { mockWebhooks } from './data/webhook';

// Fixed task id kept for backward-compat data lookups, but routes now use a
// parameter (`:taskId`) so any real currentTask.task_id from the Sidebar will
// match in mock mode. See docs/ROADMAP.md S0-P0b.
const DEFAULT_TASK_ID = 'task_01J9XXXXX';

const mockUser = {
  id: 'user_001',
  org_id: 'org_001',
  email: 'admin@eakis.local',
  display_name: '管理员',
  phone: null,
  avatar_url: null,
  is_active: true,
  last_login_at: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  role: 'super_admin',
  permissions: ['*'],
  teams: {},
};

// ─── RBAC mock data ──────────────────────────────────────
const mockUsers = [
  { id: 'user_001', org_id: 'org_001', email: 'admin@eakis.local', display_name: '管理员', phone: '13800000001', avatar_url: null, is_active: true, last_login_at: '2026-06-17T08:00:00Z', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-06-17T08:00:00Z' },
  { id: 'user_002', org_id: 'org_001', email: 'analyst@eakis.local', display_name: '张分析师', phone: '13800000002', avatar_url: null, is_active: true, last_login_at: '2026-06-16T10:00:00Z', created_at: '2026-02-01T00:00:00Z', updated_at: '2026-06-16T10:00:00Z' },
  { id: 'user_003', org_id: 'org_001', email: 'engineer@eakis.local', display_name: '李工程师', phone: '13800000003', avatar_url: null, is_active: false, last_login_at: null, created_at: '2026-03-01T00:00:00Z', updated_at: '2026-03-01T00:00:00Z' },
];

const mockTeams = [
  { id: 'team_001', org_id: 'org_001', name: '默认团队', description: '系统默认团队', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z', member_count: 2 },
  { id: 'team_002', org_id: 'org_001', name: '红队', description: '攻击演练团队', created_at: '2026-02-01T00:00:00Z', updated_at: '2026-02-01T00:00:00Z', member_count: 1 },
];

const mockTeamMembers: Record<string, Array<{ user_id: string; team_id: string; role_name: string; display_name: string; email: string; joined_at: string; invited_by?: string }>> = {
  team_001: [
    { user_id: 'user_001', team_id: 'team_001', role_name: 'super_admin', display_name: '管理员', email: 'admin@eakis.local', joined_at: '2026-01-01T00:00:00Z' },
    { user_id: 'user_002', team_id: 'team_001', role_name: 'analyst', display_name: '张分析师', email: 'analyst@eakis.local', joined_at: '2026-02-01T00:00:00Z' },
  ],
  team_002: [
    { user_id: 'user_003', team_id: 'team_002', role_name: 'engineer', display_name: '李工程师', email: 'engineer@eakis.local', joined_at: '2026-02-01T00:00:00Z' },
  ],
};

const mockAuditLogs = [
  { id: 1, user_id: 'user_001', username: 'admin@eakis.local', org_id: 'org_001', action: 'LOGIN', resource_type: 'auth', resource_id: null, ip_address: '10.0.0.1', user_agent: 'Chrome/125', request_method: 'POST', request_path: '/v1/auth/token', status_code: 200, duration_ms: 142, detail: {}, created_at: '2026-06-17T08:00:00Z' },
  { id: 2, user_id: 'user_001', username: 'admin@eakis.local', org_id: 'org_001', action: 'TASK_CREATE', resource_type: 'task', resource_id: 'task_01J9XXXXX', ip_address: '10.0.0.1', user_agent: 'Chrome/125', request_method: 'POST', request_path: '/v1/tasks', status_code: 201, duration_ms: 89, detail: { company_name: '某金融科技公司' }, created_at: '2026-06-17T08:05:00Z' },
  { id: 3, user_id: 'user_002', username: 'analyst@eakis.local', org_id: 'org_001', action: 'USER_UPDATE', resource_type: 'user', resource_id: 'user_003', ip_address: '10.0.0.2', user_agent: 'Chrome/125', request_method: 'PATCH', request_path: '/v1/admin/users/user_003', status_code: 200, duration_ms: 34, detail: {}, created_at: '2026-06-17T09:10:00Z' },
];

const paginate = <T,>(data: T[], page = 1, page_size = 20) => ({
  data,
  pagination: { page, page_size, total: data.length, total_pages: Math.max(1, Math.ceil(data.length / page_size)) },
});

// ─── Templates mock data (S4) ────────────────────────────
const mockTemplates: Array<Record<string, unknown>> = [
  { id: 'tm1', org_id: 'org_001', name: '金融行业深度扫描', template_type: 'task', description: '金融行业深度扫描(3级穿透+全模块)', content: { target_depth: 3, modules: ['M1','M3'], concurrency: 5, smart_c_segment: true }, parent_template_id: null, parent_name: null, scope: 'org', owner_id: null, team_id: null, version: 1, is_active: 1, is_seed: 0, created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
  { id: 'tm2', org_id: 'org_001', name: '资产报告-标准版', template_type: 'report', description: '资产清单标准模板', content: { report_type: 'asset', fields: ['ip','domain','port','risk_level'], format: 'md', cover: true }, parent_template_id: null, parent_name: null, scope: 'org', owner_id: null, team_id: null, version: 1, is_active: 1, is_seed: 0, created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
  { id: 'tm3', org_id: 'org_001', name: '资产报告-精简版', template_type: 'report', description: '继承标准版,仅核心字段', content: { fields: ['ip','domain','risk_level'] }, parent_template_id: 'tm2', parent_name: '资产报告-标准版', scope: 'org', owner_id: null, team_id: null, version: 1, is_active: 1, is_seed: 0, created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
  { id: 'tm4', org_id: 'org_001', name: 'keyword_extraction_v2', template_type: 'prompt', description: 'Prompt种子', content: { agent: 'M2', template: '你是关键词提取专家,请从 {{input}} 提取业务关键词', variables: ['input'] }, parent_template_id: null, parent_name: null, scope: 'org', owner_id: null, team_id: null, version: 1, is_active: 1, is_seed: 1, created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
  { id: 'tm5', org_id: 'org_001', name: 'Web应用通用攻击路径', template_type: 'attack_path', description: '信息收集→漏洞发现→利用→横向', content: { nodes: [{id:'n1',type:'recon',label:'信息收集'},{id:'n2',type:'vuln_scan',label:'漏洞扫描'},{id:'n3',type:'exploit',label:'漏洞利用'},{id:'n4',type:'lateral',label:'横向移动'}], edges: [{source:'n1',target:'n2',action:'auto'},{source:'n2',target:'n3',action:'manual'},{source:'n3',target:'n4',action:'conditional'}] }, parent_template_id: null, parent_name: null, scope: 'org', owner_id: null, team_id: null, version: 1, is_active: 1, is_seed: 0, created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
];
const mockTplTypes = { types: [
  { value: 'task', label: '任务模板', description: '任务参数预设' },
  { value: 'report', label: '报告模板', description: '报告字段勾选+布局' },
  { value: 'prompt', label: '提示词', description: 'LLM提示词' },
  { value: 'attack_path', label: '攻击路径', description: '可视化DAG' },
] };
const _tplPaginate = (data: unknown[], page = 1, page_size = 20) => ({ data, pagination: { page, page_size, total: data.length, total_pages: Math.max(1, Math.ceil(data.length / page_size)) } });
const _tplMerge = (t: Record<string, unknown>) => {
  const pid = t.parent_template_id as string | null;
  if (!pid) return t.content as Record<string, unknown>;
  const parent = mockTemplates.find((p) => p.id === pid);
  return parent ? { ...(parent.content as Record<string, unknown>), ...(t.content as Record<string, unknown>) } : t.content;
};

export const handlers = [
  // ─── Auth ───────────────────────────────────────────────
  http.get('/v1/auth/system-status', () =>
    HttpResponse.json({ initialized: true }),
  ),
  http.post('/v1/auth/init-admin', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      access_token: 'mock_access_token_init',
      refresh_token: 'mock_refresh_token_init',
      token_type: 'bearer',
      display_name: (body as Record<string, string>).display_name ?? 'admin',
    });
  }),
  http.post('/v1/auth/token', async ({ request }) => {
    // Accept both JSON and form-urlencoded
    let username = 'admin';
    try {
      const text = await request.text();
      if (text.includes('=')) {
        const params = new URLSearchParams(text);
        username = params.get('username') ?? 'admin';
      } else {
        const json = JSON.parse(text) as Record<string, string>;
        username = json.username ?? 'admin';
      }
    } catch {
      // ignore parse errors
    }
    return HttpResponse.json({
      access_token: 'mock_access_token',
      refresh_token: 'mock_refresh_token',
      token_type: 'bearer',
      username,
    });
  }),
  http.get('/v1/auth/me', () => HttpResponse.json(mockUser)),
  http.post('/v1/auth/refresh', () =>
    HttpResponse.json({
      access_token: 'mock_access_token_refreshed',
      refresh_token: 'mock_refresh_token_refreshed',
      token_type: 'bearer',
    }),
  ),
  http.post('/v1/auth/logout', () => HttpResponse.json({ success: true })),
  http.patch('/v1/auth/me/password', () => HttpResponse.json({ success: true })),

  // ─── Tasks ──────────────────────────────────────────────
  http.get('/v1/tasks', () => HttpResponse.json(paginate(mockTasks))),
  // Parameterized task routes — any task id matches (S0-P0b fix)
  http.get('/v1/tasks/:taskId', ({ params }) => {
    const id = params.taskId as string;
    return HttpResponse.json(id === DEFAULT_TASK_ID ? mockTask : { ...mockTask, task_id: id });
  }),
  http.put('/v1/tasks/:taskId', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...mockTask, task_id: params.taskId, ...body });
  }),
  http.get('/v1/tasks/:taskId/status', ({ params }) =>
    HttpResponse.json({ task_id: params.taskId, status: 'running', current_stage: 'api_crawl', progress: 0.42, error_message: null }),
  ),
  http.post('/v1/tasks/:taskId/pause', () => HttpResponse.json({ status: 'paused' })),
  http.post('/v1/tasks/:taskId/resume', () => HttpResponse.json({ status: 'running' })),
  http.post('/v1/tasks/:taskId/cancel', () => HttpResponse.json({ status: 'cancelled' })),
  http.post('/v1/tasks/:taskId/retry', ({ params }) => HttpResponse.json({ ...mockTask, task_id: params.taskId, status: 'running' })),
  http.post('/v1/tasks/batch/cancel', () => HttpResponse.json({ success: true })),
  http.post('/v1/tasks/batch/resume', () => HttpResponse.json({ success: true })),

  // ─── Keywords ───────────────────────────────────────────
  http.get('/v1/tasks/:taskId/keywords', () => HttpResponse.json({
    data: mockKeywords,
    summary: { business_count: 46, tech_count: 29, entity_count: 38, total: 113 },
    pagination: { page: 1, page_size: 20, total: mockKeywords.length, total_pages: 1 },
  })),
  http.post('/v1/tasks/:taskId/keywords', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'kw_new', ...body, confidence: 1.0, source: '人工添加', derived: false, used_in_dsl: false });
  }),

  // ─── Assets (task-scoped) ──────────────────────────────
  http.post('/v1/tasks/:taskId/assets/discover', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      task_id: params.taskId, status: 'running', total_searched: 0, total_candidates: 0,
      total_confirmed: 0, total_enriched: 0, by_asset_type: {}, avg_confidence: 0.0, errors: [],
      ...(body as object),
    }, { status: 201 });
  }),
  http.get('/v1/tasks/:taskId/assets/status', ({ params }) => HttpResponse.json({
    task_id: params.taskId, status: 'completed', total_assets: mockAssets.length,
    total_confirmed: 4, by_asset_type: { ip: 2, domain: 2, web: 1, app: 1 }, avg_confidence: 0.86,
  })),
  http.get('/v1/tasks/:taskId/assets', () => HttpResponse.json(paginate(mockAssets))),
  http.get('/v1/tasks/:taskId/assets/:assetId', ({ params }) => {
    const asset = mockAssets.find((a) => a.id === params.assetId);
    return asset ? HttpResponse.json(asset) : HttpResponse.json({ error: { code: 'NOT_FOUND', message: '资产不存在' } }, { status: 404 });
  }),

  // ─── Global Assets (S1 typed asset view + legacy category) ──
  http.get('/v1/assets', ({ request }) => {
    const url = new URL(request.url);
    const assetType = url.searchParams.get('asset_type') || url.searchParams.get('category') || '';
    const q = (url.searchParams.get('q') || '').toLowerCase();
    // 映射旧 mock 数据到 TypedAsset 格式
    const buildTyped = (a: any, type: string, typeSpecific: Record<string, unknown> = {}) => ({
      id: a.id, asset_type: type, domain: a.domain || null, ip_address: a.ip_address || null,
      port: a.port || null, risk_level: a.risk_level || 'info', confidence: a.confidence || 0.9,
      confirmed: a.confirmed ?? false, company_id: a.company_id || null, company_name: a.related_units?.[0] || null,
      tech_stack: a.tech_stack || [], icp_entity: a.icp_entity || null, waf_type: a.waf_type || null,
      status: 'confirmed', source: 'icp', notes: null, discovered_at: a.discovered_at || null,
      vuln_count: a.vuln_count || { critical: 0, high: 0, medium: 0, low: 0 },
      type_specific: typeSpecific,
    });
    const ipTyped = mockIPAssets.map((a: any) => buildTyped(a, 'ip', { ip_address: a.ip_address, is_cdn: false, asn: 'AS123', region: '北京', open_ports: a.open_ports?.join(',') }));
    const domainTyped = mockDomainAssets.map((a: any) => buildTyped(a, 'domain', { domain: a.domain, icp_license: '京ICP备12345号', registrant: '—' }));
    const webTyped = mockWebAssets.map((a: any) => buildTyped(a, 'web', {}));
    const appTyped = mockAppAssets.map((a: any) => buildTyped(a, 'app', { name: a.app_name || a.name, package_name: 'com.example.app', platform: 'android', version: '1.0', download_source: a.download_url }));
    const miniTyped = mockMiniProgramAssets.map((a: any) => buildTyped(a, 'miniprogram', { name: a.name, app_id: a.app_id, platform: 'wechat', subject_entity: '某公司', category: '工具' }));
    const certTyped = [{ id: 'cert_001', asset_type: 'certificate', domain: null, ip_address: null, port: null, risk_level: 'info', confidence: 1, confirmed: true, company_id: null, company_name: '某金融科技公司', tech_stack: [], icp_entity: null, waf_type: null, status: 'confirmed', source: 'ct_log', notes: null, discovered_at: null, vuln_count: { critical: 0, high: 0, medium: 0, low: 0 }, type_specific: { common_name: '*.target.com', issuer: "Let's Encrypt", expires_at: '2026-12-01', is_expired: false, is_self_signed: false, signature_algorithm: 'SHA256-RSA' } }];
    const all = { ip: ipTyped, domain: domainTyped, web: webTyped, app: appTyped, miniprogram: miniTyped, certificate: certTyped };
    let data = assetType ? (all as any)[assetType] || [] : [...ipTyped, ...domainTyped, ...webTyped, ...appTyped, ...miniTyped, ...certTyped];
    if (q) data = data.filter((a: any) => (a.domain || '').toLowerCase().includes(q) || (a.ip_address || '').toLowerCase().includes(q));
    return HttpResponse.json(paginate(data));
  }),
  http.get('/v1/assets/:assetId/full', ({ params }) => {
    return HttpResponse.json({
      id: params.assetId, asset_type: 'ip', domain: null, ip_address: '203.0.113.45', port: null,
      risk_level: 'high', confirmed: true, company_id: null, company_name: '某金融科技公司',
      tech_stack: ['Nginx', 'Spring Boot'], icp_entity: '某金融科技公司', waf_type: null,
      open_ports: [80, 443, 8080], cert_info: {}, notes: null, status: 'confirmed', value_score: 75,
      discovered_at: '2026-06-17T00:00:00',
      type_specific: { ip_address: '203.0.113.45', is_cdn: false, asn: 'AS123', region: '北京', open_ports: '80,443,8080' },
      vulnerabilities: [
        { id: 'v1', title: '未授权访问', severity: 'critical', vuln_type: 'UNAUTHORIZED', status: 'confirmed' },
        { id: 'v2', title: 'SQL注入', severity: 'high', vuln_type: 'SQL_INJECTION', status: 'detected' },
      ],
    });
  }),
  http.patch('/v1/assets/batch', () => HttpResponse.json({ success: true })),
  http.delete('/v1/assets/batch', () => HttpResponse.json({ success: true })),

  // ─── Interfaces (task-scoped) ───────────────────────────
  http.post('/v1/tasks/:taskId/interfaces/crawl', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      task_id: params.taskId, status: 'running', total_assets: 0, total_raw: 0,
      total_classified: 0, by_type: {}, privilege_sensitive_count: 0, errors: [],
      ...(body as object),
    }, { status: 201 });
  }),
  http.get('/v1/tasks/:taskId/interfaces/status', ({ params }) => HttpResponse.json({
    task_id: params.taskId, status: 'completed', total_interfaces: mockInterfaces.length,
    by_type: { query: 891, operation: 347, upload: 45, search: 120, auth: 89, admin: 67, other: 273 },
    privilege_sensitive_count: 312,
  })),
  http.get('/v1/tasks/:taskId/interfaces', () => HttpResponse.json({
    data: mockInterfaces,
    summary: { total: 1832, by_type: { query: 891, operation: 347, upload: 45, search: 120, auth: 89, admin: 67, other: 273 }, privilege_sensitive: 312, untested: 428 },
    pagination: { page: 1, page_size: 20, total: mockInterfaces.length, total_pages: 1 },
  })),
  http.get('/v1/tasks/:taskId/interfaces/:interfaceId', ({ params }) => {
    const iface = mockInterfaces.find((i) => i.id === params.interfaceId);
    return iface ? HttpResponse.json(iface) : HttpResponse.json({ error: { code: 'NOT_FOUND', message: '接口不存在' } }, { status: 404 });
  }),

  // ─── Vulnerabilities (task-scoped) ──────────────────────
  http.get('/v1/tasks/:taskId/vulnerabilities', () => HttpResponse.json({
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
  http.get('/v1/tasks/:taskId/vulnerabilities/:vulnId', ({ params }) => {
    const vuln = mockVulnerabilities.find((v) => v.id === params.vulnId);
    return vuln ? HttpResponse.json(vuln) : HttpResponse.json({ error: { code: 'NOT_FOUND', message: '漏洞不存在' } }, { status: 404 });
  }),
  http.get('/v1/tasks/:taskId/vulnerabilities/statistics', () => HttpResponse.json({
    by_severity: { critical: 5, high: 12, medium: 18, low: 8 },
    by_type: { PRIVILEGE_ESC: 8, SQL_INJECTION: 5, UNAUTHORIZED: 12, XSS: 6, OTHER: 12 },
    by_asset: [],
    trend: [],
    risk_score: 8.3,
    confirmed_rate: 0.72,
  })),

  // ─── Global Vulnerabilities ────────────────────────────
  http.get('/v1/vulnerabilities', () => HttpResponse.json({
    data: mockVulnerabilities,
    summary: {
      by_severity: { critical: 5, high: 12, medium: 18, low: 8 },
      by_type: { PRIVILEGE_ESC: 8, SQL_INJECTION: 5, UNAUTHORIZED: 12, XSS: 6, OTHER: 12 },
      by_asset: [],
      trend: [],
      risk_score: 8.3,
      confirmed_rate: 0.72,
    },
    pagination: { page: 1, page_size: 20, total: mockVulnerabilities.length, total_pages: 1 },
  })),
  http.get('/v1/vulnerabilities/statistics', () => HttpResponse.json({
    by_severity: { critical: 5, high: 12, medium: 18, low: 8 },
    by_type: { PRIVILEGE_ESC: 8, SQL_INJECTION: 5, UNAUTHORIZED: 12, XSS: 6, OTHER: 12 },
    by_asset: [],
    trend: [],
    risk_score: 8.3,
    confirmed_rate: 0.72,
  })),
  http.patch('/v1/vulnerabilities/batch', () => HttpResponse.json({ success: true })),
  http.delete('/v1/vulnerabilities/batch', () => HttpResponse.json({ success: true })),
  http.post('/v1/vulnerabilities/batch/retest', () => HttpResponse.json({ success: true })),

  // ─── Reports ───────────────────────────────────────────
  http.get('/v1/tasks/:taskId/reports', () => HttpResponse.json(paginate(mockReports))),
  http.get('/v1/tasks/:taskId/reports/:reportId', ({ params }) => {
    const report = mockReports.find((r) => r.report_id === params.reportId);
    if (!report) return HttpResponse.json({ error: { code: 'NOT_FOUND', message: '报告不存在' } }, { status: 404 });
    // S2: mock 报告含 content (渲染后 Markdown)
    return HttpResponse.json({
      ...report,
      content: report.content || '# 攻击面评估报告\n\n## 一、执行摘要\n\n本次评估共发现资产 6 个、漏洞 5 个。\n\n## 二、资产清单\n\n| 域名 | 风险等级 |\n| --- | --- |\n| admin.target.cn | high |\n\n## 三、漏洞详情\n\n### 1. 🔴 未授权访问 [critical]\n\n- **修复建议**: 添加鉴权\n',
    });
  }),
  http.post('/v1/tasks/:taskId/reports', ({ params }) => {
    // S2: 模拟同步生成完成 (返回 completed + 简短 content)
    const reportId = `rpt_${Date.now()}`;
    mockReports.unshift({
      report_id: reportId, status: 'completed',
      quality_score: { overall: 0.85, accuracy: 0.80, completeness: 0.90, readability: 0.90, actionability: 0.80 },
      files: { markdown: `reports/${params.taskId}/${reportId}.md` },
      content: '# 攻击面评估报告\n\n## 一、执行摘要\n\n本次评估共发现资产 6 个、漏洞 5 个，综合风险评分 25.5/100。\n\n## 二、资产清单\n\n共 6 个资产。\n\n| 类型 | 域名 | 风险 |\n| --- | --- | --- |\n| web | admin.target.cn | high |\n| web | search.target.com | high |\n\n## 三、漏洞详情\n\n共 5 个漏洞。\n\n### 1. 🔴 未授权访问 [critical]\n- **已确认**: 是\n- **修复建议**: 添加鉴权中间件\n\n---\n## 四、风险分析\n\n综合风险评分 25.5/100，整体风险等级：低危。\n\n---\n## 五、修复建议\n\n1. **[CRITICAL] 未授权访问**: 添加鉴权中间件\n',
      page_count: 3, word_count: 580, generated_at: new Date().toISOString(), generation_duration_minutes: 0,
    } as any);
    return HttpResponse.json({ report_job_id: reportId, status: 'completed', estimated_minutes: 0 }, { status: 201 });
  }),

  // ─── System ────────────────────────────────────────────
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

  // ─── Providers ──────────────────────────────────────────
  http.get('/v1/config/providers', () => HttpResponse.json({ data: mockProviders })),
  http.get('/v1/config/providers/:id', ({ params }) => {
    const p = mockProviders.find((p) => p.id === params.id);
    return p ? HttpResponse.json(p) : HttpResponse.json({ error: { code: 'NOT_FOUND' } }, { status: 404 });
  }),
  http.post('/v1/config/providers', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'prov_new', ...body, enabled: true, created_at: new Date().toISOString(), models: body.models || [] });
  }),
  http.put('/v1/config/providers/:id', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const p = mockProviders.find((p) => p.id === params.id);
    return HttpResponse.json({ ...p, ...body });
  }),
  http.delete('/v1/config/providers/:id', () => HttpResponse.json({ success: true })),
  http.get('/v1/config/model-allocations', () => HttpResponse.json(mockModelAllocations)),
  http.put('/v1/config/model-allocations/:agentName', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(body);
  }),
  http.get('/v1/config/providers/usage', () => HttpResponse.json(mockProviderUsage)),

  // ─── Companies ───────────────────────────────────────────
  http.get('/v1/companies', () => HttpResponse.json(paginate(mockCompanies))),
  http.post('/v1/companies', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'comp_new', ...body, task_count: 0, latest_task_status: null, created_at: new Date().toISOString() });
  }),
  http.get('/v1/companies/:id', ({ params }) => {
    const company = mockCompanies.find((c) => c.id === params.id);
    return company ? HttpResponse.json(company) : HttpResponse.json({ error: 'NOT_FOUND' }, { status: 404 });
  }),
  http.get('/v1/companies/:id/detail', ({ params }) => {
    const id = params.id as string;
    const detail = mockCompanyDetails[id];
    if (detail) return HttpResponse.json(detail);
    const sub = mockSubCompanies.find((s) => s.id === id);
    if (sub) {
      return HttpResponse.json({
        ...sub,
        sub_company_count: 0, hierarchy_level: 1,
        sub_companies: [],
        asset_summary: { total: 0, by_type: {} },
        vuln_summary: { total: 0, by_severity: {} },
      });
    }
    return HttpResponse.json({ error: 'NOT_FOUND' }, { status: 404 });
  }),
  http.get('/v1/companies/:id/sub-units', ({ params }) => {
    const subs = mockSubCompanies.filter((s) => s.parent_company_id === params.id);
    return HttpResponse.json(paginate(subs));
  }),
  http.get('/v1/companies/:id/osint', () => HttpResponse.json(paginate([]))),
  http.patch('/v1/companies/batch', () => HttpResponse.json({ success: true })),
  http.delete('/v1/companies/batch', () => HttpResponse.json({ success: true })),

  // ─── Companies: 企业主体采集 (云图/商业API) ───────────────
  // 字面路径必须早于 /:id 注册，避免 :id 捕获 "enrich"。
  http.get('/v1/companies/enrich/providers', () => HttpResponse.json(['yuntu'])),
  http.post('/v1/companies/enrich/batch', async ({ request }) => {
    const body = (await request.json()) as { company_ids: string[] };
    const results = (body.company_ids || []).map((cid) => ({
      company_id: cid, ok: true, error: null, new_relations: 2, conflicts: 0,
    }));
    return HttpResponse.json({
      results,
      summary: {
        success: results.length, failed: 0,
        total_relations: results.reduce((s, r) => s + r.new_relations, 0),
      },
    });
  }),
  http.post('/v1/companies/:id/enrich', async ({ params, request }) => {
    const id = params.id as string;
    const body = ((await request.json().catch(() => ({}))) || {}) as { strategy?: string };
    const detail = mockCompanyDetails[id];
    // 模拟：返回新增关系 + 1-2 个字段冲突（供前端冲突对比 Modal 演示）
    const conflicts =
      body.strategy === 'overwrite'
        ? []
        : (detail && detail.legal_person
            ? [{ field: 'legal_person', old_value: detail.legal_person, new_value: '赵六（云图）', old_source: detail.data_source, new_source: 'yuntu' }]
            : []);
    return HttpResponse.json({
      company_id: id, provider: 'yuntu', fetched_at: new Date().toISOString(),
      updated_fields: ['business_status'], new_relations: 2,
      conflicts,
      relations: [
        { id: `rel_${id}_1`, parent_company_id: id, child_company_id: `sub_${id}_1`,
          relation_type: 'holding', holding_ratio: 100, data_source: 'yuntu', created_at: new Date().toISOString() },
        { id: `rel_${id}_2`, parent_company_id: id, child_company_id: `sub_${id}_2`,
          relation_type: 'minority_stake', holding_ratio: 45, data_source: 'yuntu', created_at: new Date().toISOString() },
      ],
    });
  }),
  http.post('/v1/companies/:id/enrich/confirm', async ({ params }) => {
    return HttpResponse.json({ company_id: params.id, applied_fields: ['legal_person'] });
  }),

  // ─── Companies: S1 cascade / relations / graph / risk / search (A.1/A.7/C.3) ─
  // NOTE: /search must precede /:id routes so :id does not capture "search".
  http.get('/v1/companies/search', ({ request }) => {
    const url = new URL(request.url);
    const q = (url.searchParams.get('q') || '').toLowerCase();
    const hits = mockCompanies
      .filter((c) => c.name.toLowerCase().includes(q))
      .map((c) => ({ id: c.id, name: c.name, aliases: [], credit_code: '', industry: c.industry }));
    return HttpResponse.json({ query: q, hits });
  }),
  http.get('/v1/companies/:id/assets', ({ params }) => {
    const assets = mockAssets.filter((a: any) => a.company_id === params.id);
    return HttpResponse.json(paginate(assets));
  }),
  http.get('/v1/companies/:id/vulnerabilities', ({ params }) => {
    const assetIds = new Set(mockAssets.filter((a: any) => a.company_id === params.id).map((a: any) => a.id));
    const vulns = mockVulnerabilities.filter((v: any) => assetIds.has(v.asset_id));
    return HttpResponse.json(paginate(vulns));
  }),
  http.get('/v1/companies/:id/relations', ({ params, request }) => {
    const url = new URL(request.url);
    const direction = url.searchParams.get('direction') || 'children';
    const id = params.id as string;
    // Demo: first company is parent of second.
    const parent = mockCompanies[0];
    const child = mockCompanies[1] || parent;
    if (parent && child && id === parent.id && direction !== 'parents') {
      return HttpResponse.json([{
        id: 'rel_001', parent_company_id: parent.id, child_company_id: child.id,
        relation_type: 'holding', holding_ratio: 100.0, data_source: 'seed_sample',
        created_at: '2026-06-17T00:00:00Z',
      }]);
    }
    return HttpResponse.json([]);
  }),
  http.post('/v1/companies/:id/relations', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'rel_new', ...body, created_at: new Date().toISOString() }, { status: 201 });
  }),
  http.get('/v1/companies/:id/graph', ({ params }) => {
    const root = mockCompanies.find((c) => c.id === params.id) || mockCompanies[0];
    const child = mockCompanies[1] || root;
    return HttpResponse.json({
      root_id: root.id,
      nodes: [
        { id: root.id, name: root.name, depth: 0, source: 'direct' },
        { id: child.id, name: child.name, holding_ratio: 100, source: 'inherited', depth: 1 },
      ],
      edges: [{ source: root.id, target: child.id, relation_type: 'holding', holding_ratio: 100 }],
    });
  }),
  http.get('/v1/companies/:id/risk', ({ params }) => {
    const assetIds = new Set(mockAssets.filter((a: any) => a.company_id === params.id).map((a: any) => a.id));
    const vulns = mockVulnerabilities.filter((v: any) => assetIds.has(v.asset_id));
    const bySeverity: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    let riskScore = 0;
    for (const v of vulns) {
      const sev = (v.severity || 'info') as string;
      bySeverity[sev] = (bySeverity[sev] || 0) + 1;
      riskScore += (v.cvss_score || 0) * ({ critical: 1, high: 0.7, medium: 0.4, low: 0.1, info: 0 } as Record<string, number>)[sev];
    }
    return HttpResponse.json({
      company_id: params.id, risk_score: Math.min(riskScore, 100),
      asset_count: assetIds.size, vuln_count: vulns.length, by_severity: bySeverity,
    });
  }),
  http.get('/v1/companies/:id/risk/trend', ({ params }) => {
    // Two demo points so the trend chart has data.
    const now = new Date().toISOString();
    return HttpResponse.json({
      company_id: params.id,
      points: [
        { snapshot_at: now, risk_score: 64.2, asset_count: 5, vuln_count: 18 },
        { snapshot_at: now, risk_score: 71.5, asset_count: 6, vuln_count: 24 },
      ],
    });
  }),

  // ─── Webhooks ───────────────────────────────────────────
  http.get('/v1/config/webhooks', () => HttpResponse.json({ data: mockWebhooks })),

  // ─── Tools: S5 工具管理 (mock) ──────────────────────────
  http.get('/v1/tools', () => HttpResponse.json([
    { name: 'subfinder', binary: 'subfinder', description: 'ProjectDiscovery 子域名枚举', category: 'recon', params: [{name:'domain',input_type:'domain',flag:'-d',required:true,multiple:true}], allowed_flags: ['-all'], default_timeout: 300, enabled: true },
    { name: 'dnsx', binary: 'dnsx', description: 'DNS 解析与反查', category: 'dns', params: [{name:'domain',input_type:'domain',flag:'-d',required:false,multiple:true}], allowed_flags: [], default_timeout: 180, enabled: true },
    { name: 'httpx', binary: 'httpx', description: 'HTTP 存活探测/指纹', category: 'recon', params: [{name:'url',input_type:'url',flag:'-u',required:true,multiple:true}], allowed_flags: [], default_timeout: 300, enabled: true },
    { name: 'naabu', binary: 'naabu', description: '端口扫描', category: 'portscan', params: [{name:'host',input_type:'domain',flag:'-host',required:true,multiple:true}], allowed_flags: [], default_timeout: 600, enabled: true },
    { name: 'nmap', binary: 'nmap', description: '深度端口/服务识别', category: 'portscan', params: [{name:'host',input_type:'domain',flag:'',required:true,multiple:true}], allowed_flags: [], default_timeout: 900, enabled: true },
    { name: 'cert', binary: 'curl', description: '证书透明度查询 (crt.sh)', category: 'cert', params: [{name:'domain',input_type:'domain',flag:'',required:true,multiple:false}], allowed_flags: [], default_timeout: 60, enabled: true },
    { name: 'nuclei', binary: 'nuclei', description: '漏洞扫描 (PoC 模板)', category: 'vulnscan', params: [{name:'url',input_type:'url',flag:'-u',required:true,multiple:true}], allowed_flags: [], default_timeout: 1800, enabled: false },
  ])),
  http.get('/v1/tools/:name', ({ params }) => HttpResponse.json({ name: params.name, binary: params.name, description: 'mock', category: 'recon', params: [], allowed_flags: [], default_timeout: 300, enabled: true })),
  http.post('/v1/tools/:name/run', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    // mock: 域名输入校验 + 返回示例子域名
    const inputs = body.inputs as Record<string, unknown>;
    const domain = inputs?.domain || inputs?.url || inputs?.host;
    if (typeof domain === 'string' && /[^a-z0-9.\-:\/]/i.test(domain)) {
      return HttpResponse.json({ id: 'texe_reject', tool_name: params.name, category: 'recon', task_id: null, inputs, flags: null, status: 'invalid_input', exit_code: null, stdout: '', stderr: '', parsed: null, duration_s: 0, error: 'Invalid input', started_at: new Date().toISOString(), created_at: new Date().toISOString() }, { status: 201 });
    }
    return HttpResponse.json({ id: `texe_${Date.now()}`, tool_name: params.name, category: 'recon', task_id: body.task_id || null, inputs, flags: body.flags || null, status: 'success', exit_code: 0, stdout: '', stderr: '', parsed: ['a.example.com','b.example.com','c.example.com'], duration_s: 2.3, error: null, started_at: new Date().toISOString(), created_at: new Date().toISOString() }, { status: 201 });
  }),
  http.get('/v1/tools/:name/status', ({ params }) => HttpResponse.json({ tool_name: params.name, last_status: 'success', last_run: new Date().toISOString() })),
  http.get('/v1/tool-executions', () => HttpResponse.json({ data: [
    { id: 'texe1', tool_name: 'subfinder', category: 'recon', task_id: null, inputs: { domain: ['example.com'] }, flags: null, status: 'success', exit_code: 0, stdout: '{"host":"a.example.com"}', stderr: '', parsed: ['a.example.com','b.example.com'], duration_s: 3.2, error: null, started_at: new Date().toISOString(), created_at: new Date().toISOString() },
  ], pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 } })),
  http.get('/v1/tool-executions/:id', ({ params }) => HttpResponse.json({ id: params.id, tool_name: 'subfinder', category: 'recon', task_id: null, inputs: { domain: ['example.com'] }, flags: null, status: 'success', exit_code: 0, stdout: '{"host":"a.example.com"}', stderr: '', parsed: ['a.example.com'], duration_s: 3.2, error: null, started_at: new Date().toISOString(), created_at: new Date().toISOString() })),

  // ─── Templates: S4 模板管理 (mock data) ──────────────────
  http.get('/v1/templates/types', () => HttpResponse.json(mockTplTypes)),
  http.get('/v1/templates', ({ request }) => {
    const url = new URL(request.url);
    const tt = url.searchParams.get('template_type');
    let data = tt ? mockTemplates.filter((t) => t.template_type === tt) : mockTemplates;
    data = data.map((t) => ({ ...t, content: _tplMerge(t) }));
    return HttpResponse.json(_tplPaginate(data));
  }),
  http.post('/v1/templates', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'tm_new', org_id: 'org_001', parent_template_id: null, parent_name: null, owner_id: null, team_id: null, version: 1, is_active: 1, is_seed: 0, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), ...body }, { status: 201 });
  }),
  http.get('/v1/templates/:id', ({ params }) => {
    const t = mockTemplates.find((x) => x.id === params.id);
    return t ? HttpResponse.json({ ...t, content: _tplMerge(t) }) : HttpResponse.json({ error: 'NOT_FOUND' }, { status: 404 });
  }),
  http.patch('/v1/templates/:id', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const t = mockTemplates.find((x) => x.id === params.id);
    return HttpResponse.json({ ...t, ...body, version: (Number(t?.version || 1) + 1), updated_at: new Date().toISOString() });
  }),
  http.delete('/v1/templates/:id', () => new HttpResponse(null, { status: 204 })),

  // ─── Knowledge: S3 知识库管理 (mock data) ────────────────
  // vulns / payloads / fingerprints / datasources / handbooks
  http.get('/v1/knowledge/vulns', ({ request }) => {
    const url = new URL(request.url);
    return HttpResponse.json({
      data: [
        { id: 'kv1', name: 'Apache 路径穿越与RCE', severity: 'critical', vuln_id: 'CVE-2021-41773', vuln_type: '路径穿越/RCE', vendor: 'Apache', product: 'HTTP Server', version_range: '2.4.49', affected_scope: 'Apache 2.4.49', fingerprint_id: 'kf1', poc: 'GET /cgi-bin/.%2e/.%2e/etc/passwd', remediation: '升级至 2.4.50+', status: 'published', contributed_by: 'seed', reviewed_by: 'seed', review_comment: null, tags: ['Apache', 'RCE'], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
        { id: 'kv2', name: 'Struts2 S2-045 RCE', severity: 'critical', vuln_id: 'CVE-2017-5638', vuln_type: 'RCE', vendor: 'Apache', product: 'Struts2', version_range: '2.3.5-2.5.10', affected_scope: null, fingerprint_id: null, poc: 'Content-Type: %{...}', remediation: '升级', status: 'published', contributed_by: 'seed', reviewed_by: 'seed', review_comment: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
        { id: 'kv3', name: '未授权访问-管理后台', severity: 'high', vuln_id: null, vuln_type: '未授权访问', vendor: '通用', product: '管理后台', version_range: '*', affected_scope: null, fingerprint_id: null, poc: 'GET /admin', remediation: '添加鉴权', status: 'draft', contributed_by: 'analyst@eakis.local', reviewed_by: null, review_comment: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
      ],
      pagination: { page: Number(url.searchParams.get('page') || 1), page_size: 20, total: 3, total_pages: 1 },
    });
  }),
  http.post('/v1/knowledge/vulns', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'kv_new', ...body, status: 'draft', tags: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, { status: 201 });
  }),
  http.get('/v1/knowledge/vulns/:id', ({ params }) => HttpResponse.json({ id: params.id, name: '示例漏洞', severity: 'high', vuln_id: 'CVE-2024-XXXX', vuln_type: 'SQLi', vendor: null, product: null, version_range: null, affected_scope: null, fingerprint_id: null, poc: 'GET /?id=1\'', remediation: '参数化查询', status: 'published', contributed_by: 'seed', reviewed_by: 'seed', review_comment: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' })),
  http.patch('/v1/knowledge/vulns/:id', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: params.id, ...body, updated_at: new Date().toISOString() });
  }),
  http.delete('/v1/knowledge/vulns/:id', () => new HttpResponse(null, { status: 204 })),
  http.post('/v1/knowledge/vulns/:id/review', async ({ params, request }) => {
    const body = (await request.json()) as { action: string };
    const statusMap: Record<string, string> = { submit: 'pending_review', approve: 'published', reject: 'draft', deprecate: 'deprecated' };
    return HttpResponse.json({ id: params.id, status: statusMap[body.action], updated_at: new Date().toISOString() });
  }),

  http.get('/v1/knowledge/payloads', ({ request }) => {
    const url = new URL(request.url);
    const cat = url.searchParams.get('category');
    const all = [
      { id: 'kp1', name: '常见弱口令 TOP20', content: '123456\npassword\nadmin\nroot', category: 'pass', group_name: '常见弱口令', weight: 2.0, hit_count: 5, description: '常见弱密码', data_source: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
      { id: 'kp2', name: '敏感后台路径', content: '/admin\n/manage\n/.git/config', category: 'path', group_name: '敏感路径', weight: 1.5, hit_count: 3, description: null, data_source: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
      { id: 'kp3', name: '常见管理员用户名', content: 'admin\nroot\nadministrator', category: 'user', group_name: '常见用户名', weight: 1.0, hit_count: 2, description: null, data_source: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
      { id: 'kp4', name: '常见浏览器 UA', content: 'Mozilla/5.0 (Windows NT 10.0)\nMozilla/5.0 (Macintosh)', category: 'header', group_name: 'ua', weight: 1.0, hit_count: 0, description: '多行UA', data_source: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
      { id: 'kp5', name: '金融行业关键词', content: '银行\n证券\n基金', category: 'keywords', group_name: '行业关键词', weight: 1.2, hit_count: 0, description: null, data_source: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
    ];
    const data = cat ? all.filter((p) => p.category === cat) : all;
    return HttpResponse.json({ data, pagination: { page: 1, page_size: 20, total: data.length, total_pages: 1 } });
  }),
  http.post('/v1/knowledge/payloads', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'kp_new', ...body, hit_count: 0, tags: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, { status: 201 });
  }),
  http.get('/v1/knowledge/payloads/:id', ({ params }) => HttpResponse.json({ id: params.id, name: '示例', content: 'admin\nroot', category: 'pass', group_name: null, weight: 1.0, hit_count: 0, description: null, data_source: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' })),
  http.patch('/v1/knowledge/payloads/:id', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: params.id, ...body, updated_at: new Date().toISOString() });
  }),
  http.delete('/v1/knowledge/payloads/:id', () => new HttpResponse(null, { status: 204 })),
  http.post('/v1/knowledge/payloads/:id/hit', ({ params }) => HttpResponse.json({ id: params.id, hit_count: 999, updated_at: new Date().toISOString() })),

  http.get('/v1/knowledge/fingerprints', () => HttpResponse.json({
    data: [
      { id: 'kf1', name: 'Nginx HTTP Server', category: 'service', component: 'Nginx', version: '1.x', match_type: 'header', match_rule: 'Server: nginx', description: 'Nginx 指纹', status: 'published', contributed_by: 'seed', reviewed_by: 'seed', tags: [], vuln_count: 0, created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
      { id: 'kf2', name: 'Apache HTTPD', category: 'service', component: 'Apache', version: '2.4.x', match_type: 'header', match_rule: 'Server: Apache', description: 'Apache 指纹', status: 'published', contributed_by: 'seed', reviewed_by: 'seed', tags: [], vuln_count: 1, created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
    ],
    pagination: { page: 1, page_size: 20, total: 2, total_pages: 1 },
  })),
  http.post('/v1/knowledge/fingerprints', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'kf_new', ...body, status: 'draft', tags: [], vuln_count: 0, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, { status: 201 });
  }),
  http.get('/v1/knowledge/fingerprints/:id', ({ params }) => HttpResponse.json({ id: params.id, name: '示例指纹', category: null, component: null, version: null, match_type: 'header', match_rule: 'X', description: null, status: 'draft', contributed_by: null, reviewed_by: null, tags: [], vuln_count: 0, created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' })),
  http.patch('/v1/knowledge/fingerprints/:id', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: params.id, ...body, updated_at: new Date().toISOString() });
  }),
  http.delete('/v1/knowledge/fingerprints/:id', () => new HttpResponse(null, { status: 204 })),

  http.get('/v1/knowledge/datasources', () => HttpResponse.json({
    data: [
      { id: 'kd1', name: 'Fofa 资产搜索引擎', platform: 'fofa', api_base_url: 'https://fofa.info/api', config: '{"fields":["host","ip"]}', description: '白帽汇', is_active: 1, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
      { id: 'kd2', name: 'Shodan', platform: 'shodan', api_base_url: 'https://api.shodan.io', config: '{}', description: 'Shodan', is_active: 1, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
    ],
    pagination: { page: 1, page_size: 20, total: 2, total_pages: 1 },
  })),
  http.post('/v1/knowledge/datasources', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'kd_new', ...body, is_active: 1, tags: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, { status: 201 });
  }),
  http.patch('/v1/knowledge/datasources/:id', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: params.id, ...body, updated_at: new Date().toISOString() });
  }),
  http.delete('/v1/knowledge/datasources/:id', () => new HttpResponse(null, { status: 204 })),

  http.get('/v1/knowledge/handbooks', () => HttpResponse.json({
    data: [
      { id: 'kh1', title: 'SQL注入应急响应流程', category: '应急响应', content: '## SQL注入应急\n1. 隔离\n2. 分析日志', summary: '标准应急步骤', status: 'published', contributed_by: 'seed', reviewed_by: 'seed', review_comment: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
      { id: 'kh2', title: '越权漏洞检测经验', category: '攻击案例', content: '## 越权检测\n- 水平越权', summary: null, status: 'draft', contributed_by: 'analyst@eakis.local', reviewed_by: null, review_comment: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' },
    ],
    pagination: { page: 1, page_size: 20, total: 2, total_pages: 1 },
  })),
  http.post('/v1/knowledge/handbooks', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'kh_new', ...body, status: 'draft', tags: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, { status: 201 });
  }),
  http.get('/v1/knowledge/handbooks/:id', ({ params }) => HttpResponse.json({ id: params.id, title: '示例手册', category: null, content: '内容', summary: null, status: 'draft', contributed_by: null, reviewed_by: null, review_comment: null, tags: [], created_at: '2026-06-17T00:00:00Z', updated_at: '2026-06-17T00:00:00Z' })),
  http.patch('/v1/knowledge/handbooks/:id', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: params.id, ...body, updated_at: new Date().toISOString() });
  }),
  http.delete('/v1/knowledge/handbooks/:id', () => new HttpResponse(null, { status: 204 })),
  http.post('/v1/config/webhooks', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 'wh_new', ...body, enabled: true, last_triggered_at: null, last_status: null, failure_count: 0, created_at: new Date().toISOString() });
  }),
  http.put('/v1/config/webhooks/:id', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(body);
  }),
  http.delete('/v1/config/webhooks/:id', () => HttpResponse.json({ success: true })),
  http.post('/v1/config/webhooks/:id/test', () => HttpResponse.json({ success: true, response_time_ms: 245 })),

  // ─── RBAC: Users ────────────────────────────────────────
  http.get('/v1/admin/users', ({ request }) => {
    const url = new URL(request.url);
    const isActive = url.searchParams.get('is_active');
    let data = mockUsers;
    if (isActive !== null) data = mockUsers.filter((u) => u.is_active === (isActive === 'true'));
    return HttpResponse.json(paginate(data));
  }),
  http.post('/v1/admin/users', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: `user_${String(mockUsers.length + 1).padStart(3, '0')}`, org_id: 'org_001',
      is_active: true, last_login_at: null,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      avatar_url: null, ...body,
    }, { status: 201 });
  }),
  http.get('/v1/admin/users/:userId', ({ params }) => {
    const u = mockUsers.find((x) => x.id === params.userId);
    return u ? HttpResponse.json(u) : HttpResponse.json({ error: 'NOT_FOUND' }, { status: 404 });
  }),
  http.patch('/v1/admin/users/:userId', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const u = mockUsers.find((x) => x.id === params.userId);
    return HttpResponse.json({ ...u, ...body, updated_at: new Date().toISOString() });
  }),
  http.delete('/v1/admin/users/:userId', () => new HttpResponse(null, { status: 204 })),

  // ─── RBAC: Teams ────────────────────────────────────────
  http.get('/v1/admin/teams', () => HttpResponse.json(paginate(mockTeams))),
  http.post('/v1/admin/teams', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: `team_${String(mockTeams.length + 1).padStart(3, '0')}`, org_id: 'org_001',
      member_count: 0, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      ...body,
    }, { status: 201 });
  }),
  http.get('/v1/admin/teams/:teamId', ({ params }) => {
    const t = mockTeams.find((x) => x.id === params.teamId);
    if (!t) return HttpResponse.json({ error: 'NOT_FOUND' }, { status: 404 });
    return HttpResponse.json({ ...t, members: mockTeamMembers[t.id] || [] });
  }),
  http.patch('/v1/admin/teams/:teamId', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const t = mockTeams.find((x) => x.id === params.teamId);
    return HttpResponse.json({ ...t, ...body, updated_at: new Date().toISOString() });
  }),
  http.delete('/v1/admin/teams/:teamId', () => new HttpResponse(null, { status: 204 })),
  http.post('/v1/admin/teams/:teamId/members', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...body, team_id: params.teamId, joined_at: new Date().toISOString() }, { status: 201 });
  }),
  http.patch('/v1/admin/teams/:teamId/members/:userId', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(body);
  }),
  http.delete('/v1/admin/teams/:teamId/members/:userId', () => new HttpResponse(null, { status: 204 })),

  // ─── RBAC: Audit Logs ───────────────────────────────────
  http.get('/v1/admin/audit-logs', ({ request }) => {
    const url = new URL(request.url);
    const action = url.searchParams.get('action');
    const resourceType = url.searchParams.get('resource_type');
    let data = mockAuditLogs;
    if (action) data = data.filter((l) => l.action === action);
    if (resourceType) data = data.filter((l) => l.resource_type === resourceType);
    return HttpResponse.json(paginate(data));
  }),
  http.get('/v1/admin/audit-logs/:logId', ({ params }) => {
    const l = mockAuditLogs.find((x) => x.id === Number(params.logId));
    return l ? HttpResponse.json(l) : HttpResponse.json({ error: 'NOT_FOUND' }, { status: 404 });
  }),
];
