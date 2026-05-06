# AttackScope AI 前端框架实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 AttackScope AI 前端框架骨架 — 全部 8 个页面可访问，共享组件可用，Mock 数据层可运行。

**Architecture:** React 18 + TypeScript 5 单体 SPA，Vite 构建，Ant Design 5 暗色主题。API 层通过 MSW 实现双模式（Mock/真实），全局状态用 Zustand，实时数据用 WebSocket hook。

**Tech Stack:** React 18, TypeScript 5, Vite 6, Ant Design 5, React Router 6, Zustand, Axios, MSW 2

**Spec:** `docs/superpowers/specs/2026-05-06-frontend-framework-design.md`

---

## File Structure Map

### 配置文件 (5)
| 文件 | 职责 |
|------|------|
| `web/package.json` | 依赖声明、脚本 |
| `web/vite.config.ts` | Vite 构建配置、代理 |
| `web/tsconfig.json` | TypeScript 配置 |
| `web/.env.development` | `VITE_API_MOCK=true` |
| `web/.env.production` | `VITE_API_MOCK=false` |

### 入口 (3)
| 文件 | 职责 |
|------|------|
| `web/index.html` | HTML 模板 |
| `web/src/main.tsx` | React 渲染入口，MSW 条件加载 |
| `web/src/App.tsx` | 根组件，Provider 包裹 |

### 类型 (6)
| 文件 | 职责 |
|------|------|
| `web/src/types/api.ts` | 分页、错误响应、通用类型 |
| `web/src/types/task.ts` | 任务、阶段、事件类型 |
| `web/src/types/keyword.ts` | 关键词类型 |
| `web/src/types/asset.ts` | 资产、证书、漏洞统计类型 |
| `web/src/types/interface.ts` | 接口、参数类型 |
| `web/src/types/vulnerability.ts` | 漏洞、证据、统计类型 |

### API 层 (9)
| 文件 | 职责 |
|------|------|
| `web/src/api/client.ts` | Axios 实例、拦截器 |
| `web/src/api/tasks.ts` | 任务 CRUD + 操作 |
| `web/src/api/keywords.ts` | 关键词 CRUD |
| `web/src/api/assets.ts` | 资产列表/详情/导出 |
| `web/src/api/interfaces.ts` | 接口列表/详情/标记 |
| `web/src/api/vulnerabilities.ts` | 漏洞列表/详情/统计 |
| `web/src/api/reports.ts` | 报告生成/状态/下载 |
| `web/src/api/system.ts` | 健康检查/指标/配置 |
| `web/src/api/mock/handlers.ts` | MSW 请求处理器 |

### Mock 数据 (7)
| 文件 | 职责 |
|------|------|
| `web/src/api/mock/browser.ts` | MSW browser worker 初始化 |
| `web/src/api/mock/data/task.ts` | 任务 Mock 数据 |
| `web/src/api/mock/data/keyword.ts` | 关键词 Mock 数据 |
| `web/src/api/mock/data/asset.ts` | 资产 Mock 数据 |
| `web/src/api/mock/data/interface.ts` | 接口 Mock 数据 |
| `web/src/api/mock/data/vulnerability.ts` | 漏洞 Mock 数据 |
| `web/src/api/mock/data/report.ts` | 报告 Mock 数据 |

### 状态 (2)
| 文件 | 职责 |
|------|------|
| `web/src/store/appStore.ts` | 全局 UI 状态（侧边栏、主题） |
| `web/src/store/taskStore.ts` | 当前任务状态 |

### 布局组件 (2)
| 文件 | 职责 |
|------|------|
| `web/src/components/Layout/AppLayout.tsx` | 主布局（侧边栏+顶栏+内容区） |
| `web/src/components/Layout/Sidebar.tsx` | 侧边栏导航 |

### 共享组件 (5)
| 文件 | 职责 |
|------|------|
| `web/src/components/AgentPipeline/index.tsx` | Agent 五层流程管线 |
| `web/src/components/MetricCard/index.tsx` | 指标卡片 |
| `web/src/components/AgentLog/index.tsx` | 实时日志流 |
| `web/src/components/RiskTag/index.tsx` | 风险等级标签 |
| `web/src/components/StatusBadge/index.tsx` | 状态徽章 |

### 路由 (1)
| 文件 | 职责 |
|------|------|
| `web/src/router.tsx` | React Router 路由配置 |

### Hooks (2)
| 文件 | 职责 |
|------|------|
| `web/src/hooks/useTaskEvents.ts` | WebSocket 事件流 |
| `web/src/hooks/usePagination.ts` | 分页逻辑 |

### 页面 (8)
| 文件 | 职责 |
|------|------|
| `web/src/pages/Dashboard/index.tsx` | 总览仪表盘 |
| `web/src/pages/Keywords/index.tsx` | 关键词生成 |
| `web/src/pages/Assets/index.tsx` | 资产关联 |
| `web/src/pages/Interfaces/index.tsx` | 接口爬取 |
| `web/src/pages/Pentest/index.tsx` | 自动渗透 |
| `web/src/pages/Vulnerabilities/index.tsx` | 漏洞库 |
| `web/src/pages/Reports/index.tsx` | 报告中心 |
| `web/src/pages/Settings/index.tsx` | 系统设置 |

**总计: ~50 个文件**

---

## Task 1: 项目初始化与依赖安装

**Files:**
- Create: `web/package.json`
- Create: `web/index.html`
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/tsconfig.node.json`
- Create: `web/.env.development`
- Create: `web/.env.production`

- [ ] **Step 1: 创建 Vite 项目**

```bash
cd d:/Users/Spence/Desktop/EAKIS
npm create vite@latest web -- --template react-ts
```

- [ ] **Step 2: 安装依赖**

```bash
cd web
npm install antd @ant-design/icons react-router-dom zustand axios
npm install -D msw
```

- [ ] **Step 3: 配置 vite.config.ts**

替换 `web/vite.config.ts` 内容：

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 4: 创建环境变量文件**

`web/.env.development`:
```
VITE_API_MOCK=true
VITE_API_BASE_URL=http://localhost:8000
```

`web/.env.production`:
```
VITE_API_MOCK=false
VITE_API_BASE_URL=https://api.attackscope.example.com
```

- [ ] **Step 5: 更新 tsconfig.json 添加路径别名**

在 `web/tsconfig.json` 的 `compilerOptions` 中添加：

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

（保留 Vite 生成的其他配置项）

- [ ] **Step 6: 验证项目可启动**

```bash
cd web && npm run dev
```

预期：浏览器访问 http://localhost:3000 看到 Vite + React 默认页面。

- [ ] **Step 7: 提交**

```bash
git add web/
git commit -m "feat: 初始化前端项目 (Vite + React + TypeScript)"
```

---

## Task 2: TypeScript 类型定义

**Files:**
- Create: `web/src/types/api.ts`
- Create: `web/src/types/task.ts`
- Create: `web/src/types/keyword.ts`
- Create: `web/src/types/asset.ts`
- Create: `web/src/types/interface.ts`
- Create: `web/src/types/vulnerability.ts`

- [ ] **Step 1: 创建通用 API 类型**

`web/src/types/api.ts`:

```typescript
export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string;
    timestamp: string;
  };
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}
```

- [ ] **Step 2: 创建任务类型**

`web/src/types/task.ts`:

```typescript
export type TaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
export type StageName = 'intelligence' | 'keyword_gen' | 'asset_discovery' | 'api_crawl' | 'pentest' | 'report_gen';
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface TaskStage {
  stage: StageName;
  status: StageStatus;
}

export interface CreateTaskRequest {
  company_name: string;
  company_aliases: string[];
  industry: string;
  authorized_scope: {
    domains: string[];
    ip_ranges: string[];
    exclude: string[];
  };
  config: {
    keyword_types: string[];
    asset_platforms: string[];
    crawl_depth: number;
    pentest_enabled: boolean;
    pentest_intensity: string;
    notification_webhook?: string;
  };
}

export interface TaskStats {
  assets_found: number;
  assets_confirmed: number;
  interfaces_crawled: number;
  vulns_detected: number;
  vulns_confirmed: number;
}

export interface StageDetail {
  status: StageStatus;
  duration_s?: number;
  items?: number;
  keywords?: number;
  assets?: number;
  confirmed?: number;
  progress?: number;
  interfaces?: number;
}

export interface Task {
  task_id: string;
  company_name: string;
  status: TaskStatus;
  current_stage: StageName | null;
  progress: number;
  stats: TaskStats;
  stage_details: Record<StageName, StageDetail>;
  created_at: string;
  started_at: string | null;
  estimated_completion: string | null;
  estimated_duration_hours?: number;
  stages?: TaskStage[];
}

export type TaskEventType = 'stage_progress' | 'agent_log' | 'vuln_found' | 'task_complete' | 'error';

export interface TaskEvent {
  event_type: TaskEventType;
  timestamp: string;
  data: {
    stage?: string;
    progress?: number;
    message: string;
    agent?: string;
  };
}
```

- [ ] **Step 3: 创建关键词类型**

`web/src/types/keyword.ts`:

```typescript
export type KeywordType = 'business' | 'tech' | 'entity';

export interface Keyword {
  id: string;
  word: string;
  type: KeywordType;
  weight: number;
  confidence: number;
  source: string;
  derived: boolean;
  used_in_dsl: boolean;
}

export interface KeywordSummary {
  business_count: number;
  tech_count: number;
  entity_count: number;
  total: number;
}

export interface CreateKeywordRequest {
  word: string;
  type: KeywordType;
  weight: number;
  reason?: string;
}
```

- [ ] **Step 4: 创建资产类型**

`web/src/types/asset.ts`:

```typescript
export type AssetType = 'web' | 'api' | 'mobile' | 'infra';
export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface CertInfo {
  subject: string;
  issuer: string;
  expires_at: string;
}

export interface VulnCount {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface Asset {
  id: string;
  domain: string;
  ip_address: string;
  asset_type: AssetType;
  confidence: number;
  risk_level: RiskLevel;
  icp_verified: boolean;
  waf_detected: string | null;
  tech_stack: string[];
  open_ports: number[];
  cert_info: CertInfo | null;
  vuln_count: VulnCount;
  interface_count: number;
  discovered_at: string;
}

export interface AssetListParams {
  risk?: RiskLevel;
  confirmed?: boolean;
  asset_type?: AssetType;
  icp_verified?: boolean;
  has_waf?: boolean;
  tech_stack?: string;
}

export interface UpdateAssetRequest {
  confirmed?: boolean;
  risk_level?: RiskLevel;
  notes?: string;
}
```

- [ ] **Step 5: 创建接口类型**

`web/src/types/interface.ts`:

```typescript
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
export type ApiType = 'query' | 'operation' | 'upload' | 'search' | 'auth' | 'admin' | 'other';

export interface InterfaceParam {
  name: string;
  location: 'path' | 'query' | 'header' | 'body';
  type: string;
  required: boolean;
  sensitive: boolean;
}

export interface ApiInterface {
  id: string;
  asset_id: string;
  path: string;
  method: HttpMethod;
  api_type: ApiType;
  parameters: InterfaceParam[];
  auth_required: boolean;
  privilege_sensitive: boolean;
  sensitive_params: string[];
  trigger_scenario: string;
  test_priority: number;
  crawl_method: 'dynamic' | 'static';
  vuln_tested: boolean;
  vuln_count: number;
  version: number;
  crawled_at: string;
}

export interface InterfaceSummary {
  total: number;
  by_type: Record<ApiType, number>;
  privilege_sensitive: number;
  untested: number;
}

export interface UpdateInterfaceRequest {
  test_priority?: number;
  notes?: string;
  skip_test?: boolean;
}
```

- [ ] **Step 6: 创建漏洞类型**

`web/src/types/vulnerability.ts`:

```typescript
import { RiskLevel } from './asset';

export type VulnStatus = 'confirmed' | 'false_positive' | 'fixed' | 'wont_fix';
export type FalsePositiveRisk = 'HIGH' | 'MED' | 'LOW';

export interface VulnEvidence {
  request: string;
  response_code: number;
  response_snippet: string;
}

export interface Vulnerability {
  id: string;
  asset_id: string;
  interface_id: string;
  vuln_type: string;
  severity: RiskLevel;
  cvss_score: number;
  title: string;
  description: string;
  affected_path: string;
  test_payload: string;
  evidence: VulnEvidence;
  llm_confidence: number;
  false_positive_risk: FalsePositiveRisk;
  remediation: string;
  status: VulnStatus;
  confirmed_at: string | null;
  discovered_at: string;
}

export interface VulnStatistics {
  by_severity: Record<RiskLevel, number>;
  by_type: Record<string, number>;
  by_asset: Array<{
    asset_id: string;
    domain: string;
    vuln_count: number;
    max_severity: RiskLevel;
  }>;
  trend: unknown[];
  risk_score: number;
  confirmed_rate: number;
}

export interface UpdateVulnRequest {
  status: VulnStatus;
  human_confirmed?: boolean;
  notes?: string;
  confirmed_by?: string;
}
```

- [ ] **Step 7: 提交**

```bash
git add web/src/types/
git commit -m "feat: 添加 TypeScript 类型定义 (API/Task/Keyword/Asset/Interface/Vuln)"
```

---

## Task 3: API 客户端层

**Files:**
- Create: `web/src/api/client.ts`
- Create: `web/src/api/tasks.ts`
- Create: `web/src/api/keywords.ts`
- Create: `web/src/api/assets.ts`
- Create: `web/src/api/interfaces.ts`
- Create: `web/src/api/vulnerabilities.ts`
- Create: `web/src/api/reports.ts`
- Create: `web/src/api/system.ts`

- [ ] **Step 1: 创建 Axios 客户端**

`web/src/api/client.ts`:

```typescript
import axios from 'axios';
import type { ApiError } from '@/types/api';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.error) {
      const apiError: ApiError = error.response.data;
      console.error(`[${apiError.error.code}] ${apiError.error.message}`);
    }
    return Promise.reject(error);
  },
);

export default client;
```

- [ ] **Step 2: 创建任务 API**

`web/src/api/tasks.ts`:

```typescript
import client from './client';
import type { Task, CreateTaskRequest } from '@/types/task';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const createTask = (data: CreateTaskRequest) =>
  client.post<Task>('/v1/tasks', data).then((r) => r.data);

export const getTask = (taskId: string) =>
  client.get<Task>(`/v1/tasks/${taskId}`).then((r) => r.data);

export const listTasks = (params?: PaginationParams & { status?: string }) =>
  client.get<PaginatedResponse<Task>>('/v1/tasks', { params }).then((r) => r.data);

export const pauseTask = (taskId: string) =>
  client.post(`/v1/tasks/${taskId}/pause`);

export const resumeTask = (taskId: string) =>
  client.post(`/v1/tasks/${taskId}/resume`);

export const cancelTask = (taskId: string) =>
  client.post(`/v1/tasks/${taskId}/cancel`);

export const retryTask = (taskId: string) =>
  client.post(`/v1/tasks/${taskId}/retry`);
```

- [ ] **Step 3: 创建关键词 API**

`web/src/api/keywords.ts`:

```typescript
import client from './client';
import type { Keyword, KeywordSummary, CreateKeywordRequest } from '@/types/keyword';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getKeywords = (taskId: string, params?: PaginationParams & { type?: string; min_weight?: number }) =>
  client.get<PaginatedResponse<Keyword> & { summary: KeywordSummary }>(`/v1/tasks/${taskId}/keywords`, { params }).then((r) => r.data);

export const addKeyword = (taskId: string, data: CreateKeywordRequest) =>
  client.post<Keyword>(`/v1/tasks/${taskId}/keywords`, data).then((r) => r.data);

export const deleteKeyword = (taskId: string, keywordId: string) =>
  client.delete(`/v1/tasks/${taskId}/keywords/${keywordId}`);
```

- [ ] **Step 4: 创建资产 API**

`web/src/api/assets.ts`:

```typescript
import client from './client';
import type { Asset, AssetListParams, UpdateAssetRequest } from '@/types/asset';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getAssets = (taskId: string, params?: PaginationParams & AssetListParams) =>
  client.get<PaginatedResponse<Asset>>(`/v1/tasks/${taskId}/assets`, { params }).then((r) => r.data);

export const getAsset = (taskId: string, assetId: string) =>
  client.get<Asset>(`/v1/tasks/${taskId}/assets/${assetId}`).then((r) => r.data);

export const updateAsset = (taskId: string, assetId: string, data: UpdateAssetRequest) =>
  client.patch<Asset>(`/v1/tasks/${taskId}/assets/${assetId}`, data).then((r) => r.data);

export const exportAssets = (taskId: string, format: 'csv' | 'xlsx' | 'json') =>
  client.get(`/v1/tasks/${taskId}/assets/export`, { params: { format }, responseType: 'blob' });
```

- [ ] **Step 5: 创建接口 API**

`web/src/api/interfaces.ts`:

```typescript
import client from './client';
import type { ApiInterface, InterfaceSummary, UpdateInterfaceRequest } from '@/types/interface';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getInterfaces = (taskId: string, params?: PaginationParams & {
  asset_id?: string;
  type?: string;
  privilege_sensitive?: boolean;
  auth_required?: boolean;
  min_priority?: number;
  method?: string;
}) =>
  client.get<PaginatedResponse<ApiInterface> & { summary: InterfaceSummary }>(`/v1/tasks/${taskId}/interfaces`, { params }).then((r) => r.data);

export const getInterface = (taskId: string, interfaceId: string) =>
  client.get<ApiInterface>(`/v1/tasks/${taskId}/interfaces/${interfaceId}`).then((r) => r.data);

export const updateInterface = (taskId: string, interfaceId: string, data: UpdateInterfaceRequest) =>
  client.patch<ApiInterface>(`/v1/tasks/${taskId}/interfaces/${interfaceId}`, data).then((r) => r.data);
```

- [ ] **Step 6: 创建漏洞 API**

`web/src/api/vulnerabilities.ts`:

```typescript
import client from './client';
import type { Vulnerability, VulnStatistics, UpdateVulnRequest } from '@/types/vulnerability';
import type { RiskLevel } from '@/types/asset';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getVulnerabilities = (taskId: string, params?: PaginationParams & {
  severity?: RiskLevel;
  vuln_type?: string;
  confirmed?: boolean;
  false_positive_risk?: string;
  asset_id?: string;
}) =>
  client.get<PaginatedResponse<Vulnerability> & { summary: VulnStatistics }>(`/v1/tasks/${taskId}/vulnerabilities`, { params }).then((r) => r.data);

export const getVulnerability = (taskId: string, vulnId: string) =>
  client.get<Vulnerability>(`/v1/tasks/${taskId}/vulnerabilities/${vulnId}`).then((r) => r.data);

export const updateVulnerability = (taskId: string, vulnId: string, data: UpdateVulnRequest) =>
  client.patch<Vulnerability>(`/v1/tasks/${taskId}/vulnerabilities/${vulnId}`, data).then((r) => r.data);

export const getVulnStatistics = (taskId: string) =>
  client.get<VulnStatistics>(`/v1/tasks/${taskId}/vulnerabilities/statistics`).then((r) => r.data);
```

- [ ] **Step 7: 创建报告 API**

`web/src/api/reports.ts`:

```typescript
import client from './client';
import type { PaginatedResponse } from '@/types/api';

export interface GenerateReportRequest {
  format: ('markdown' | 'pdf')[];
  sections: ('summary' | 'assets' | 'interfaces' | 'vulns' | 'remediation')[];
  language: string;
  template: 'standard' | 'detailed' | 'executive';
}

export interface ReportJob {
  report_job_id: string;
  status: string;
  estimated_minutes: number;
}

export interface Report {
  report_id: string;
  status: string;
  quality_score: {
    overall: number;
    accuracy: number;
    completeness: number;
    readability: number;
    actionability: number;
  };
  files: Record<string, string>;
  page_count: number;
  word_count: number;
  generated_at: string;
  generation_duration_minutes: number;
}

export const generateReport = (taskId: string, data: GenerateReportRequest) =>
  client.post<ReportJob>(`/v1/tasks/${taskId}/reports`, data).then((r) => r.data);

export const getReport = (taskId: string, reportId: string) =>
  client.get<Report>(`/v1/tasks/${taskId}/reports/${reportId}`).then((r) => r.data);

export const downloadReport = (taskId: string, reportId: string, format: 'pdf' | 'markdown') =>
  client.get(`/v1/tasks/${taskId}/reports/${reportId}/download`, { params: { format }, responseType: 'blob' });

export const listReports = (taskId: string) =>
  client.get<PaginatedResponse<Report>>(`/v1/tasks/${taskId}/reports`).then((r) => r.data);
```

- [ ] **Step 8: 创建系统 API**

`web/src/api/system.ts`:

```typescript
import client from './client';

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  components: Record<string, { status: string; latency_ms?: number; lag?: number; pool_size?: number }>;
}

export interface MetricsResponse {
  active_tasks: number;
  queued_tasks: number;
  completed_tasks_today: number;
  avg_task_duration_h: number;
  llm_calls_today: number;
  llm_cost_usd_today: number;
  assets_discovered_today: number;
  vulns_confirmed_today: number;
  api_requests_per_min: number;
}

export interface AgentConfig {
  model: string;
  temperature: number;
  max_tokens: number;
  timeout_s: number;
  retry_attempts: number;
  enabled: boolean;
}

export const getHealth = () =>
  client.get<HealthResponse>('/v1/health').then((r) => r.data);

export const getMetrics = () =>
  client.get<MetricsResponse>('/v1/metrics').then((r) => r.data);

export const getAgentConfigs = () =>
  client.get<Record<string, AgentConfig>>('/v1/config/agents').then((r) => r.data);

export const getAgentConfig = (agentName: string) =>
  client.get<AgentConfig>(`/v1/config/agents/${agentName}`).then((r) => r.data);

export const updateAgentConfig = (agentName: string, data: Partial<AgentConfig>) =>
  client.put<AgentConfig>(`/v1/config/agents/${agentName}`, data).then((r) => r.data);
```

- [ ] **Step 9: 提交**

```bash
git add web/src/api/
git commit -m "feat: 添加 API 客户端层 (Axios + 8 个 API 模块)"
```

---

## Task 4: Mock 数据

**Files:**
- Create: `web/src/api/mock/data/task.ts`
- Create: `web/src/api/mock/data/keyword.ts`
- Create: `web/src/api/mock/data/asset.ts`
- Create: `web/src/api/mock/data/interface.ts`
- Create: `web/src/api/mock/data/vulnerability.ts`
- Create: `web/src/api/mock/data/report.ts`

- [ ] **Step 1: 创建任务 Mock 数据**

`web/src/api/mock/data/task.ts`:

```typescript
import type { Task } from '@/types/task';

export const mockTask: Task = {
  task_id: 'task_01J9XXXXX',
  company_name: '某金融科技公司',
  status: 'running',
  current_stage: 'api_crawl',
  progress: 0.68,
  stats: {
    assets_found: 247,
    assets_confirmed: 189,
    interfaces_crawled: 1832,
    vulns_detected: 43,
    vulns_confirmed: 31,
  },
  stage_details: {
    intelligence: { status: 'completed', duration_s: 180, items: 1250 },
    keyword_gen: { status: 'completed', keywords: 113 },
    asset_discovery: { status: 'completed', assets: 247, confirmed: 189 },
    api_crawl: { status: 'running', progress: 0.76, interfaces: 1832 },
    pentest: { status: 'pending' },
    report_gen: { status: 'pending' },
  },
  created_at: '2024-01-01T08:00:00Z',
  started_at: '2024-01-01T08:01:00Z',
  estimated_completion: '2024-01-01T16:00:00Z',
};

export const mockTasks: Task[] = [mockTask];
```

- [ ] **Step 2: 创建关键词 Mock 数据**

`web/src/api/mock/data/keyword.ts`:

```typescript
import type { Keyword } from '@/types/keyword';

export const mockKeywords: Keyword[] = [
  { id: 'kw_001', word: '第三方支付', type: 'business', weight: 0.92, confidence: 0.96, source: '新闻报道:36氪', derived: false, used_in_dsl: true },
  { id: 'kw_002', word: '金融科技', type: 'business', weight: 0.89, confidence: 0.94, source: '行业分类', derived: false, used_in_dsl: true },
  { id: 'kw_003', word: '消费信贷', type: 'business', weight: 0.85, confidence: 0.91, source: '官网产品页', derived: false, used_in_dsl: true },
  { id: 'kw_004', word: 'Spring Boot', type: 'tech', weight: 0.88, confidence: 0.93, source: '技术栈识别', derived: false, used_in_dsl: true },
  { id: 'kw_005', word: 'Nginx', type: 'tech', weight: 0.82, confidence: 0.90, source: 'HTTP Header', derived: false, used_in_dsl: true },
  { id: 'kw_006', word: 'Redis', type: 'tech', weight: 0.78, confidence: 0.87, source: '端口扫描', derived: true, used_in_dsl: true },
  { id: 'kw_007', word: 'XX科技有限公司', type: 'entity', weight: 0.95, confidence: 0.98, source: '企业注册信息', derived: false, used_in_dsl: true },
  { id: 'kw_008', word: 'XX支付', type: 'entity', weight: 0.93, confidence: 0.97, source: '品牌关联', derived: true, used_in_dsl: true },
  { id: 'kw_009', word: '在线转账', type: 'business', weight: 0.81, confidence: 0.88, source: '用户行为分析', derived: true, used_in_dsl: false },
  { id: 'kw_010', word: 'MySQL', type: 'tech', weight: 0.75, confidence: 0.85, source: '错误页面泄露', derived: true, used_in_dsl: true },
];
```

- [ ] **Step 3: 创建资产 Mock 数据**

`web/src/api/mock/data/asset.ts`:

```typescript
import type { Asset } from '@/types/asset';

export const mockAssets: Asset[] = [
  {
    id: 'asset_001', domain: 'api.target.com', ip_address: '203.0.113.45',
    asset_type: 'api', confidence: 0.96, risk_level: 'high',
    icp_verified: true, waf_detected: null,
    tech_stack: ['Spring Boot 2.7', 'Nginx 1.24', 'Redis'],
    open_ports: [80, 443, 8080],
    cert_info: { subject: 'api.target.com', issuer: "Let's Encrypt", expires_at: '2024-06-01' },
    vuln_count: { critical: 1, high: 3, medium: 5, low: 2 },
    interface_count: 89, discovered_at: '2024-01-01T09:00:00Z',
  },
  {
    id: 'asset_002', domain: 'admin.target.cn', ip_address: '203.0.113.46',
    asset_type: 'web', confidence: 0.94, risk_level: 'high',
    icp_verified: true, waf_detected: null,
    tech_stack: ['Vue 3', 'Nginx 1.24'],
    open_ports: [80, 443],
    cert_info: { subject: 'admin.target.cn', issuer: "Let's Encrypt", expires_at: '2024-06-15' },
    vuln_count: { critical: 0, high: 2, medium: 4, low: 1 },
    interface_count: 34, discovered_at: '2024-01-01T09:05:00Z',
  },
  {
    id: 'asset_003', domain: 'search.target.com', ip_address: '203.0.113.47',
    asset_type: 'web', confidence: 0.91, risk_level: 'high',
    icp_verified: true, waf_detected: 'Cloudflare',
    tech_stack: ['Elasticsearch 8.x', 'Nginx 1.24'],
    open_ports: [80, 443, 9200],
    cert_info: null,
    vuln_count: { critical: 1, high: 1, medium: 2, low: 0 },
    interface_count: 12, discovered_at: '2024-01-01T09:10:00Z',
  },
  {
    id: 'asset_004', domain: 'upload.target.com', ip_address: '203.0.113.48',
    asset_type: 'web', confidence: 0.88, risk_level: 'medium',
    icp_verified: true, waf_detected: null,
    tech_stack: ['MinIO', 'Nginx 1.24'],
    open_ports: [80, 443, 9000],
    cert_info: { subject: 'upload.target.com', issuer: "Let's Encrypt", expires_at: '2024-07-01' },
    vuln_count: { critical: 0, high: 0, medium: 3, low: 2 },
    interface_count: 8, discovered_at: '2024-01-01T09:15:00Z',
  },
  {
    id: 'asset_005', domain: 'h5.target.com', ip_address: '203.0.113.49',
    asset_type: 'mobile', confidence: 0.90, risk_level: 'medium',
    icp_verified: true, waf_detected: null,
    tech_stack: ['React', 'Webpack 5'],
    open_ports: [80, 443],
    cert_info: { subject: 'h5.target.com', issuer: "Let's Encrypt", expires_at: '2024-05-20' },
    vuln_count: { critical: 0, high: 1, medium: 2, low: 1 },
    interface_count: 22, discovered_at: '2024-01-01T09:20:00Z',
  },
  {
    id: 'asset_006', domain: 'static.target.com', ip_address: '203.0.113.50',
    asset_type: 'infra', confidence: 0.85, risk_level: 'low',
    icp_verified: true, waf_detected: 'Cloudflare',
    tech_stack: ['Nginx 1.24', 'CDN'],
    open_ports: [80, 443],
    cert_info: null,
    vuln_count: { critical: 0, high: 0, medium: 0, low: 3 },
    interface_count: 2, discovered_at: '2024-01-01T09:25:00Z',
  },
];
```

- [ ] **Step 4: 创建接口 Mock 数据**

`web/src/api/mock/data/interface.ts`:

```typescript
import type { ApiInterface } from '@/types/interface';

export const mockInterfaces: ApiInterface[] = [
  {
    id: 'iface_001', asset_id: 'asset_001', path: '/api/v2/user/{userId}/orders', method: 'GET',
    api_type: 'query', parameters: [
      { name: 'userId', location: 'path', type: 'integer', required: true, sensitive: true },
      { name: 'page', location: 'query', type: 'integer', required: false, sensitive: false },
    ],
    auth_required: true, privilege_sensitive: true, sensitive_params: ['userId'],
    trigger_scenario: '点击订单列表', test_priority: 9, crawl_method: 'dynamic',
    vuln_tested: true, vuln_count: 2, version: 1, crawled_at: '2024-01-01T10:00:00Z',
  },
  {
    id: 'iface_002', asset_id: 'asset_001', path: '/api/v2/auth/login', method: 'POST',
    api_type: 'auth', parameters: [
      { name: 'username', location: 'body', type: 'string', required: true, sensitive: false },
      { name: 'password', location: 'body', type: 'string', required: true, sensitive: true },
      { name: 'captcha', location: 'body', type: 'string', required: true, sensitive: false },
    ],
    auth_required: false, privilege_sensitive: false, sensitive_params: ['password'],
    trigger_scenario: '登录操作', test_priority: 8, crawl_method: 'dynamic',
    vuln_tested: true, vuln_count: 1, version: 1, crawled_at: '2024-01-01T10:05:00Z',
  },
  {
    id: 'iface_003', asset_id: 'asset_002', path: '/admin/api/users', method: 'GET',
    api_type: 'admin', parameters: [
      { name: 'role', location: 'query', type: 'string', required: false, sensitive: false },
    ],
    auth_required: true, privilege_sensitive: true, sensitive_params: [],
    trigger_scenario: '管理员用户列表', test_priority: 10, crawl_method: 'dynamic',
    vuln_tested: true, vuln_count: 1, version: 1, crawled_at: '2024-01-01T10:10:00Z',
  },
  {
    id: 'iface_004', asset_id: 'asset_001', path: '/api/v2/transfer', method: 'POST',
    api_type: 'operation', parameters: [
      { name: 'to_account', location: 'body', type: 'string', required: true, sensitive: true },
      { name: 'amount', location: 'body', type: 'number', required: true, sensitive: true },
    ],
    auth_required: true, privilege_sensitive: true, sensitive_params: ['to_account', 'amount'],
    trigger_scenario: '转账操作', test_priority: 10, crawl_method: 'dynamic',
    vuln_tested: false, vuln_count: 0, version: 1, crawled_at: '2024-01-01T10:15:00Z',
  },
  {
    id: 'iface_005', asset_id: 'asset_003', path: '/search', method: 'GET',
    api_type: 'search', parameters: [
      { name: 'q', location: 'query', type: 'string', required: true, sensitive: false },
    ],
    auth_required: false, privilege_sensitive: false, sensitive_params: [],
    trigger_scenario: '搜索功能', test_priority: 7, crawl_method: 'static',
    vuln_tested: true, vuln_count: 1, version: 1, crawled_at: '2024-01-01T10:20:00Z',
  },
];
```

- [ ] **Step 5: 创建漏洞 Mock 数据**

`web/src/api/mock/data/vulnerability.ts`:

```typescript
import type { Vulnerability } from '@/types/vulnerability';

export const mockVulnerabilities: Vulnerability[] = [
  {
    id: 'vuln_001', asset_id: 'asset_001', interface_id: 'iface_001',
    vuln_type: 'PRIVILEGE_ESCALATION', severity: 'high', cvss_score: 8.1,
    title: '订单查询接口存在水平越权',
    description: '攻击者可通过修改 userId 参数查看任意用户的订单信息',
    affected_path: 'GET /api/v2/user/{userId}/orders',
    test_payload: '将 userId=1001 替换为 userId=9999',
    evidence: {
      request: 'GET /api/v2/user/9999/orders HTTP/1.1\nAuthorization: Bearer eyJ...',
      response_code: 200,
      response_snippet: '{"data":[{"orderId":"2024xxxx","userId":9999,"amount":5000}]}',
    },
    llm_confidence: 0.97, false_positive_risk: 'LOW',
    remediation: '服务端验证当前登录用户ID与请求参数userId是否一致，不一致时返回403',
    status: 'confirmed', confirmed_at: null, discovered_at: '2024-01-01T14:00:00Z',
  },
  {
    id: 'vuln_002', asset_id: 'asset_003', interface_id: 'iface_005',
    vuln_type: 'SQL_INJECTION', severity: 'critical', cvss_score: 9.8,
    title: '搜索接口存在SQL注入漏洞',
    description: '搜索参数未进行过滤，可注入恶意SQL语句',
    affected_path: 'GET /search?q=',
    test_payload: "q=1' OR '1'='1",
    evidence: {
      request: "GET /search?q=1'%20OR%20'1'='1 HTTP/1.1",
      response_code: 200,
      response_snippet: '{"total":15432,"results":[...]}',
    },
    llm_confidence: 0.99, false_positive_risk: 'LOW',
    remediation: '使用参数化查询，对用户输入进行严格过滤和白名单校验',
    status: 'confirmed', confirmed_at: null, discovered_at: '2024-01-01T14:30:00Z',
  },
  {
    id: 'vuln_003', asset_id: 'asset_001', interface_id: 'iface_002',
    vuln_type: 'UNAUTHORIZED', severity: 'high', cvss_score: 7.5,
    title: '登录接口缺少速率限制',
    description: '登录接口未设置速率限制，可被暴力破解',
    affected_path: 'POST /api/v2/auth/login',
    test_payload: '短时间内发送1000次登录请求',
    evidence: {
      request: 'POST /api/v2/auth/login HTTP/1.1\n{"username":"admin","password":"wrong1"}',
      response_code: 401,
      response_snippet: '{"error":"invalid_credentials"}',
    },
    llm_confidence: 0.92, false_positive_risk: 'MED',
    remediation: '添加基于IP和账号的速率限制，连续失败5次后锁定15分钟',
    status: 'confirmed', confirmed_at: null, discovered_at: '2024-01-01T15:00:00Z',
  },
  {
    id: 'vuln_004', asset_id: 'asset_005', interface_id: 'iface_005',
    vuln_type: 'XSS', severity: 'medium', cvss_score: 5.4,
    title: '移动端页面存在反射型XSS',
    description: 'URL参数未转义直接渲染到页面中',
    affected_path: 'GET /h5/redirect?url=',
    test_payload: 'url=javascript:alert(document.cookie)',
    evidence: {
      request: 'GET /h5/redirect?url=javascript:alert(1) HTTP/1.1',
      response_code: 200,
      response_snippet: '<script>window.location="javascript:alert(1)"</script>',
    },
    llm_confidence: 0.88, false_positive_risk: 'MED',
    remediation: '对URL参数进行白名单校验，使用HttpOnly和Secure标记Cookie',
    status: 'confirmed', confirmed_at: null, discovered_at: '2024-01-01T15:30:00Z',
  },
  {
    id: 'vuln_005', asset_id: 'asset_004', interface_id: 'iface_005',
    vuln_type: 'FILE_UPLOAD', severity: 'medium', cvss_score: 6.5,
    title: '文件上传接口缺少类型校验',
    description: '可上传恶意脚本文件，导致远程代码执行',
    affected_path: 'POST /upload/file',
    test_payload: '上传 .jsp webshell 文件',
    evidence: {
      request: 'POST /upload/file HTTP/1.1\nContent-Type: multipart/form-data',
      response_code: 200,
      response_snippet: '{"url":"/files/shell.jsp","status":"ok"}',
    },
    llm_confidence: 0.94, false_positive_risk: 'LOW',
    remediation: '服务端校验文件类型和内容，限制上传目录不可执行',
    status: 'confirmed', confirmed_at: null, discovered_at: '2024-01-01T16:00:00Z',
  },
];
```

- [ ] **Step 6: 创建报告 Mock 数据**

`web/src/api/mock/data/report.ts`:

```typescript
import type { Report } from '@/api/reports';

export const mockReports: Report[] = [
  {
    report_id: 'report_001',
    status: 'completed',
    quality_score: { overall: 0.93, accuracy: 0.96, completeness: 0.91, readability: 0.94, actionability: 0.89 },
    files: {
      markdown: 'https://storage.example.com/reports/rpt_001.md',
      pdf: 'https://storage.example.com/reports/rpt_001.pdf',
    },
    page_count: 47,
    word_count: 8234,
    generated_at: '2024-01-01T16:00:00Z',
    generation_duration_minutes: 18,
  },
];
```

- [ ] **Step 7: 提交**

```bash
git add web/src/api/mock/data/
git commit -m "feat: 添加 Mock 数据 (Task/Keyword/Asset/Interface/Vuln/Report)"
```

---

## Task 5: MSW Handler 与 Browser Worker

**Files:**
- Create: `web/src/api/mock/browser.ts`
- Create: `web/src/api/mock/handlers.ts`

- [ ] **Step 1: 初始化 MSW Service Worker**

```bash
cd web && npx msw init public/ --save
```

- [ ] **Step 2: 创建 MSW handlers**

`web/src/api/mock/handlers.ts`:

```typescript
import { http, HttpResponse } from 'msw';
import { mockTasks, mockTask } from './data/task';
import { mockKeywords } from './data/keyword';
import { mockAssets } from './data/asset';
import { mockInterfaces } from './data/interface';
import { mockVulnerabilities } from './data/vulnerability';
import { mockReports } from './data/report';

const TASK_ID = 'task_01J9XXXXX';

export const handlers = [
  // 任务
  http.get('/v1/tasks', () => HttpResponse.json({
    data: mockTasks,
    pagination: { page: 1, page_size: 20, total: mockTasks.length, total_pages: 1 },
  })),

  http.get(`/v1/tasks/${TASK_ID}`, () => HttpResponse.json(mockTask)),

  http.post(`/v1/tasks/${TASK_ID}/pause`, () => HttpResponse.json({ status: 'paused' })),
  http.post(`/v1/tasks/${TASK_ID}/resume`, () => HttpResponse.json({ status: 'running' })),
  http.post(`/v1/tasks/${TASK_ID}/cancel`, () => HttpResponse.json({ status: 'cancelled' })),

  // 关键词
  http.get(`/v1/tasks/${TASK_ID}/keywords`, () => HttpResponse.json({
    data: mockKeywords,
    summary: { business_count: 46, tech_count: 29, entity_count: 38, total: 113 },
    pagination: { page: 1, page_size: 20, total: mockKeywords.length, total_pages: 1 },
  })),

  http.post(`/v1/tasks/${TASK_ID}/keywords`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ id: 'kw_new', ...body, confidence: 1.0, source: '人工添加', derived: false, used_in_dsl: false });
  }),

  // 资产
  http.get(`/v1/tasks/${TASK_ID}/assets`, () => HttpResponse.json({
    data: mockAssets,
    pagination: { page: 1, page_size: 20, total: mockAssets.length, total_pages: 1 },
  })),

  http.get(`/v1/tasks/${TASK_ID}/assets/:assetId`, ({ params }) => {
    const asset = mockAssets.find((a) => a.id === params.assetId);
    return asset ? HttpResponse.json(asset) : HttpResponse.json({ error: { code: 'NOT_FOUND', message: '资产不存在' } }, { status: 404 });
  }),

  // 接口
  http.get(`/v1/tasks/${TASK_ID}/interfaces`, () => HttpResponse.json({
    data: mockInterfaces,
    summary: { total: 1832, by_type: { query: 891, operation: 347, upload: 45, search: 120, auth: 89, admin: 67, other: 273 }, privilege_sensitive: 312, untested: 428 },
    pagination: { page: 1, page_size: 20, total: mockInterfaces.length, total_pages: 1 },
  })),

  http.get(`/v1/tasks/${TASK_ID}/interfaces/:interfaceId`, ({ params }) => {
    const iface = mockInterfaces.find((i) => i.id === params.interfaceId);
    return iface ? HttpResponse.json(iface) : HttpResponse.json({ error: { code: 'NOT_FOUND', message: '接口不存在' } }, { status: 404 });
  }),

  // 漏洞
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

  // 报告
  http.get(`/v1/tasks/${TASK_ID}/reports`, () => HttpResponse.json({
    data: mockReports,
    pagination: { page: 1, page_size: 20, total: mockReports.length, total_pages: 1 },
  })),

  http.get(`/v1/tasks/${TASK_ID}/reports/:reportId`, ({ params }) => {
    const report = mockReports.find((r) => r.report_id === params.reportId);
    return report ? HttpResponse.json(report) : HttpResponse.json({ error: { code: 'NOT_FOUND', message: '报告不存在' } }, { status: 404 });
  }),

  // 系统
  http.get('/v1/health', () => HttpResponse.json({
    status: 'healthy',
    version: 'v2.0.0',
    timestamp: new Date().toISOString(),
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
    active_tasks: 3,
    queued_tasks: 7,
    completed_tasks_today: 12,
    avg_task_duration_h: 6.2,
    llm_calls_today: 4821,
    llm_cost_usd_today: 12.47,
    assets_discovered_today: 1832,
    vulns_confirmed_today: 127,
    api_requests_per_min: 342,
  })),

  http.get('/v1/config/agents', () => HttpResponse.json({
    'KEYWORD-GEN': { model: 'qwen2.5-7b', temperature: 0.1, max_tokens: 2048, timeout_s: 30, retry_attempts: 3, enabled: true },
    'ASSET-DISCOVER': { model: 'qwen2.5-7b', temperature: 0.1, max_tokens: 2048, timeout_s: 60, retry_attempts: 3, enabled: true },
    'APICRAWL-BROWSER': { model: 'gpt-4o-mini', temperature: 0.2, max_tokens: 4096, timeout_s: 120, retry_attempts: 2, enabled: true },
    'PENTEST-AUTO': { model: 'gpt-4o', temperature: 0.3, max_tokens: 4096, timeout_s: 300, retry_attempts: 2, enabled: true },
    'REPORT-GEN': { model: 'qwen2.5-72b', temperature: 0.5, max_tokens: 8192, timeout_s: 600, retry_attempts: 1, enabled: true },
  })),
];
```

- [ ] **Step 3: 创建 browser worker**

`web/src/api/mock/browser.ts`:

```typescript
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);
```

- [ ] **Step 4: 提交**

```bash
git add web/src/api/mock/ web/public/mockServiceWorker.js
git commit -m "feat: 添加 MSW Mock Handler 和 Browser Worker"
```

---

## Task 6: Zustand Store

**Files:**
- Create: `web/src/store/appStore.ts`
- Create: `web/src/store/taskStore.ts`

- [ ] **Step 1: 创建全局 UI 状态 Store**

`web/src/store/appStore.ts`:

```typescript
import { create } from 'zustand';

interface AppState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}));
```

- [ ] **Step 2: 创建任务状态 Store**

`web/src/store/taskStore.ts`:

```typescript
import { create } from 'zustand';
import type { Task, TaskEvent } from '@/types/task';

interface TaskState {
  currentTask: Task | null;
  setCurrentTask: (task: Task) => void;
  events: TaskEvent[];
  addEvent: (event: TaskEvent) => void;
  clearEvents: () => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  currentTask: null,
  setCurrentTask: (task) => set({ currentTask: task }),
  events: [],
  addEvent: (event) => set((state) => ({ events: [...state.events.slice(-200), event] })),
  clearEvents: () => set({ events: [] }),
}));
```

- [ ] **Step 3: 提交**

```bash
git add web/src/store/
git commit -m "feat: 添加 Zustand Store (appStore + taskStore)"
```

---

## Task 7: 布局组件

**Files:**
- Create: `web/src/components/Layout/Sidebar.tsx`
- Create: `web/src/components/Layout/AppLayout.tsx`

- [ ] **Step 1: 创建 Sidebar 组件**

`web/src/components/Layout/Sidebar.tsx`:

```tsx
import { useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  KeyOutlined,
  CloudServerOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  BugOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useAppStore } from '@/store/appStore';

const { Sider } = Layout;

const coreMenuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '总览仪表盘' },
  { key: '/keywords', icon: <KeyOutlined />, label: '关键词生成' },
  { key: '/assets', icon: <CloudServerOutlined />, label: '资产关联' },
  { key: '/interfaces', icon: <ApiOutlined />, label: '接口爬取' },
  { key: '/pentest', icon: <ThunderboltOutlined />, label: '自动渗透' },
];

const outputMenuItems = [
  { key: '/reports', icon: <FileTextOutlined />, label: '报告中心' },
  { key: '/vulnerabilities', icon: <BugOutlined />, label: '漏洞库' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
];

const Sidebar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);

  const selectedKey = '/' + location.pathname.split('/').filter(Boolean)[0];

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      trigger={null}
      width={220}
      style={{
        background: '#141422',
        borderRight: '1px solid #2a2a4e',
      }}
    >
      <div
        style={{
          height: 48,
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? 0 : '0 16px',
          borderBottom: '1px solid #2a2a4e',
        }}
      >
        <div style={{ fontSize: 16, fontWeight: 600, color: '#378ADD', whiteSpace: 'nowrap' }}>
          {collapsed ? 'AS' : 'AttackScope AI'}
        </div>
      </div>
      {!collapsed && (
        <div style={{ padding: '8px 16px 4px', fontSize: 10, color: '#666', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          核心流程
        </div>
      )}
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        items={coreMenuItems}
        onClick={({ key }) => navigate(key)}
        style={{ background: 'transparent', borderInlineEnd: 'none' }}
      />
      {!collapsed && (
        <div style={{ padding: '8px 16px 4px', fontSize: 10, color: '#666', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          输出管理
        </div>
      )}
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        items={outputMenuItems}
        onClick={({ key }) => navigate(key)}
        style={{ background: 'transparent', borderInlineEnd: 'none' }}
      />
    </Sider>
  );
};

export default Sidebar;
```

- [ ] **Step 2: 创建 AppLayout 组件**

`web/src/components/Layout/AppLayout.tsx`:

```tsx
import { Layout, Button, Select, Badge } from 'antd';
import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAppStore } from '@/store/appStore';
import { useTaskStore } from '@/store/taskStore';

const { Header, Content } = Layout;

const AppLayout: React.FC = () => {
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const currentTask = useTaskStore((s) => s.currentTask);
  const setCurrentTask = useTaskStore((s) => s.setCurrentTask);

  return (
    <Layout style={{ height: '100vh' }}>
      <Sidebar />
      <Layout>
        <Header
          style={{
            padding: '0 20px',
            background: '#141422',
            borderBottom: '1px solid #2a2a4e',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 48,
            lineHeight: '48px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={toggleSidebar}
              style={{ color: '#aaa' }}
            />
            <Select
              value={currentTask?.task_id}
              style={{ width: 280 }}
              placeholder="选择任务"
              size="small"
              options={[{ value: 'task_01J9XXXXX', label: '某金融科技公司' }]}
              onChange={() => {
                setCurrentTask({
                  task_id: 'task_01J9XXXXX',
                  company_name: '某金融科技公司',
                  status: 'running',
                  current_stage: 'api_crawl',
                  progress: 0.68,
                  stats: { assets_found: 247, assets_confirmed: 189, interfaces_crawled: 1832, vulns_detected: 43, vulns_confirmed: 31 },
                  stage_details: {
                    intelligence: { status: 'completed', duration_s: 180, items: 1250 },
                    keyword_gen: { status: 'completed', keywords: 113 },
                    asset_discovery: { status: 'completed', assets: 247, confirmed: 189 },
                    api_crawl: { status: 'running', progress: 0.76, interfaces: 1832 },
                    pentest: { status: 'pending' },
                    report_gen: { status: 'pending' },
                  },
                  created_at: '2024-01-01T08:00:00Z',
                  started_at: '2024-01-01T08:01:00Z',
                  estimated_completion: '2024-01-01T16:00:00Z',
                });
              }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {currentTask && (
              <Badge status={currentTask.status === 'running' ? 'processing' : 'default'} text={
                <span style={{ fontSize: 12, color: currentTask.status === 'running' ? '#52c41a' : '#999' }}>
                  {currentTask.status === 'running' ? '执行中' : currentTask.status}
                </span>
              } />
            )}
          </div>
        </Header>
        <Content style={{ overflow: 'auto', padding: 20, background: '#0d0d1a' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
```

- [ ] **Step 3: 提交**

```bash
git add web/src/components/Layout/
git commit -m "feat: 添加布局组件 (AppLayout + Sidebar)"
```

---

## Task 8: 共享组件

**Files:**
- Create: `web/src/components/RiskTag/index.tsx`
- Create: `web/src/components/StatusBadge/index.tsx`
- Create: `web/src/components/MetricCard/index.tsx`
- Create: `web/src/components/AgentPipeline/index.tsx`
- Create: `web/src/components/AgentLog/index.tsx`

- [ ] **Step 1: 创建 RiskTag 组件**

`web/src/components/RiskTag/index.tsx`:

```tsx
import { Tag } from 'antd';
import type { RiskLevel } from '@/types/asset';

const riskConfig: Record<RiskLevel, { color: string; label: string }> = {
  critical: { color: '#cf1322', label: '严重' },
  high: { color: '#d4380d', label: '高危' },
  medium: { color: '#d48806', label: '中危' },
  low: { color: '#389e0d', label: '低危' },
  info: { color: '#378ADD', label: '信息' },
};

interface RiskTagProps {
  level: RiskLevel;
}

const RiskTag: React.FC<RiskTagProps> = ({ level }) => {
  const config = riskConfig[level];
  return <Tag color={config.color} style={{ margin: 0 }}>{config.label}</Tag>;
};

export default RiskTag;
```

- [ ] **Step 2: 创建 StatusBadge 组件**

`web/src/components/StatusBadge/index.tsx`:

```tsx
import { Badge } from 'antd';
import type { TaskStatus, StageStatus } from '@/types/task';

const statusMap: Record<string, { status: 'success' | 'processing' | 'default' | 'error' | 'warning'; text: string }> = {
  pending: { status: 'default', text: '等待' },
  running: { status: 'processing', text: '运行中' },
  completed: { status: 'success', text: '完成' },
  failed: { status: 'error', text: '失败' },
  paused: { status: 'warning', text: '已暂停' },
  cancelled: { status: 'default', text: '已取消' },
};

interface StatusBadgeProps {
  status: TaskStatus | StageStatus;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const config = statusMap[status] || statusMap.pending;
  return <Badge status={config.status} text={<span style={{ fontSize: 12 }}>{config.text}</span>} />;
};

export default StatusBadge;
```

- [ ] **Step 3: 创建 MetricCard 组件**

`web/src/components/MetricCard/index.tsx`:

```tsx
import { Card, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

interface MetricCardProps {
  title: string;
  value: number | string;
  suffix?: string;
  delta?: string;
  deltaType?: 'up' | 'down';
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, suffix, delta, deltaType }) => (
  <Card
    size="small"
    style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
    styles={{ body: { padding: '14px 16px' } }}
  >
    <Statistic
      title={<span style={{ fontSize: 12, color: '#888' }}>{title}</span>}
      value={value}
      suffix={suffix}
      valueStyle={{ fontSize: 22, fontWeight: 500, color: '#e0e0e0' }}
    />
    {delta && (
      <div style={{ fontSize: 11, marginTop: 4, color: deltaType === 'up' ? '#52c41a' : '#ff4d4f' }}>
        {deltaType === 'up' ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {delta}
      </div>
    )}
  </Card>
);

export default MetricCard;
```

- [ ] **Step 4: 创建 AgentPipeline 组件**

`web/src/components/AgentPipeline/index.tsx`:

```tsx
import { Steps, Progress } from 'antd';
import {
  SearchOutlined,
  TagOutlined,
  CloudServerOutlined,
  ApiOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import StatusBadge from '@/components/StatusBadge';
import type { StageName, StageDetail } from '@/types/task';

const stageConfig: Record<StageName, { icon: React.ReactNode; label: string }> = {
  intelligence: { icon: <SearchOutlined />, label: '情报收集' },
  keyword_gen: { icon: <TagOutlined />, label: '关键词生成' },
  asset_discovery: { icon: <CloudServerOutlined />, label: '资产关联' },
  api_crawl: { icon: <ApiOutlined />, label: '接口爬取' },
  pentest: { icon: <ThunderboltOutlined />, label: '自动渗透' },
  report_gen: { icon: <ThunderboltOutlined />, label: '报告生成' },
};

const stageColors: Record<string, string> = {
  intelligence: '#378ADD',
  keyword_gen: '#378ADD',
  asset_discovery: '#639922',
  api_crawl: '#BA7517',
  pentest: '#534AB7',
  report_gen: '#534AB7',
};

interface AgentPipelineProps {
  stageDetails: Record<StageName, StageDetail>;
}

const AgentPipeline: React.FC<AgentPipelineProps> = ({ stageDetails }) => (
  <Steps direction="vertical" size="small" current={-1} style={{ marginTop: 8 }}>
    {(Object.keys(stageConfig) as StageName[]).map((stage) => {
      const detail = stageDetails[stage];
      const config = stageConfig[stage];
      const isDone = detail.status === 'completed';
      const isRunning = detail.status === 'running';
      const progress = detail.progress ?? (isDone ? 1 : 0);

      return (
        <Steps.Step
          key={stage}
          icon={
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 32,
              height: 32,
              borderRadius: 6,
              background: isDone || isRunning ? `${stageColors[stage]}22` : '#2a2a4e',
              color: isDone || isRunning ? stageColors[stage] : '#666',
            }}>
              {config.icon}
            </span>
          }
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: isDone || isRunning ? '#e0e0e0' : '#666' }}>
                {config.label}
              </span>
              <StatusBadge status={detail.status} />
            </div>
          }
          description={
            <div style={{ opacity: isDone || isRunning ? 1 : 0.5 }}>
              {isDone && detail.keywords && <span style={{ fontSize: 11, color: '#888' }}>已生成 {detail.keywords} 个关键词</span>}
              {isDone && detail.assets && <span style={{ fontSize: 11, color: '#888' }}>发现 {detail.assets} 个资产 · 确认 {detail.confirmed}</span>}
              {isRunning && <span style={{ fontSize: 11, color: '#888' }}>已采集 {detail.interfaces} 个接口</span>}
              {!isDone && !isRunning && <span style={{ fontSize: 11, color: '#666' }}>等待</span>}
              {(isRunning || isDone) && (
                <Progress
                  percent={Math.round(progress * 100)}
                  showInfo={false}
                  strokeColor={stageColors[stage]}
                  size="small"
                  style={{ marginTop: 4 }}
                />
              )}
            </div>
          }
        />
      );
    })}
  </Steps>
);

export default AgentPipeline;
```

- [ ] **Step 5: 创建 AgentLog 组件**

`web/src/components/AgentLog/index.tsx`:

```tsx
import { useRef, useEffect } from 'react';
import type { TaskEvent } from '@/types/task';

const logColors: Record<string, string> = {
  stage_progress: '#378ADD',
  agent_log: '#52c41a',
  vuln_found: '#faad14',
  task_complete: '#52c41a',
  error: '#ff4d4f',
};

const logIcons: Record<string, string> = {
  stage_progress: '[→]',
  agent_log: '[✓]',
  vuln_found: '[!]',
  task_complete: '[✓]',
  error: '[✗]',
};

interface AgentLogProps {
  events: TaskEvent[];
  maxHeight?: number;
}

const AgentLog: React.FC<AgentLogProps> = ({ events, maxHeight = 160 }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  return (
    <div style={{ fontFamily: 'monospace', fontSize: 11, maxHeight, overflowY: 'auto', lineHeight: 1.8 }}>
      {events.map((event, i) => (
        <div key={i} style={{ display: 'flex', gap: 8 }}>
          <span style={{ color: '#666', flexShrink: 0 }}>
            {new Date(event.timestamp).toLocaleTimeString('zh-CN', { hour12: false })}
          </span>
          <span style={{ color: logColors[event.event_type] || '#888' }}>
            {logIcons[event.event_type] || '[·]'}
          </span>
          <span style={{ color: '#bbb' }}>{event.data.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
};

export default AgentLog;
```

- [ ] **Step 6: 提交**

```bash
git add web/src/components/
git commit -m "feat: 添加共享组件 (RiskTag/StatusBadge/MetricCard/AgentPipeline/AgentLog)"
```

---

## Task 9: 路由 + 入口文件

**Files:**
- Create: `web/src/router.tsx`
- Create: `web/src/App.tsx`
- Create: `web/src/main.tsx`

- [ ] **Step 1: 创建路由配置**

`web/src/router.tsx`:

```tsx
import { createBrowserRouter } from 'react-router-dom';
import AppLayout from '@/components/Layout/AppLayout';
import Dashboard from '@/pages/Dashboard';
import Keywords from '@/pages/Keywords';
import Assets from '@/pages/Assets';
import Interfaces from '@/pages/Interfaces';
import Pentest from '@/pages/Pentest';
import Vulnerabilities from '@/pages/Vulnerabilities';
import Reports from '@/pages/Reports';
import Settings from '@/pages/Settings';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'keywords', element: <Keywords /> },
      { path: 'assets', element: <Assets /> },
      { path: 'interfaces', element: <Interfaces /> },
      { path: 'pentest', element: <Pentest /> },
      { path: 'vulnerabilities', element: <Vulnerabilities /> },
      { path: 'reports', element: <Reports /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
]);
```

- [ ] **Step 2: 创建 App 入口**

`web/src/App.tsx`:

```tsx
import { RouterProvider } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { router } from './router';

const App: React.FC = () => (
  <ConfigProvider
    locale={zhCN}
    theme={{
      algorithm: theme.darkAlgorithm,
      token: {
        colorPrimary: '#378ADD',
        borderRadius: 6,
        fontSize: 13,
        colorBgContainer: '#1a1a2e',
        colorBgElevated: '#1a1a2e',
        colorBorderSecondary: '#2a2a4e',
      },
      components: {
        Layout: {
          siderBg: '#141422',
          headerBg: '#141422',
          bodyBg: '#0d0d1a',
        },
        Menu: {
          darkItemBg: 'transparent',
          darkItemSelectedBg: '#378ADD22',
          darkItemHoverBg: '#ffffff0a',
        },
        Table: {
          headerBg: '#1a1a2e',
          rowHoverBg: '#ffffff0a',
        },
        Card: {
          colorBorderSecondary: '#2a2a4e',
        },
      },
    }}
  >
    <RouterProvider router={router} />
  </ConfigProvider>
);

export default App;
```

- [ ] **Step 3: 创建 main.tsx 入口（含 MSW 条件加载）**

`web/src/main.tsx`:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

async function bootstrap() {
  if (import.meta.env.VITE_API_MOCK === 'true') {
    const { worker } = await import('./api/mock/browser');
    await worker.start({ onUnhandledRequest: 'bypass' });
  }

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}

bootstrap();
```

- [ ] **Step 4: 删除 Vite 默认生成的文件**

```bash
rm -f web/src/App.css web/src/index.css web/src/assets/react.svg
```

- [ ] **Step 5: 验证编译通过**

```bash
cd web && npx tsc --noEmit
```

预期：无类型错误。

- [ ] **Step 6: 提交**

```bash
git add web/src/router.tsx web/src/App.tsx web/src/main.tsx
git add web/src/ -u
git commit -m "feat: 添加路由配置 + App/Main 入口 (含 MSW 条件加载)"
```

---

## Task 10: Dashboard 页面

**Files:**
- Create: `web/src/pages/Dashboard/index.tsx`

- [ ] **Step 1: 创建 Dashboard 页面**

`web/src/pages/Dashboard/index.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { Row, Col, Card, Table, Button, Space } from 'antd';
import { getTask } from '@/api/tasks';
import MetricCard from '@/components/MetricCard';
import AgentPipeline from '@/components/AgentPipeline';
import AgentLog from '@/components/AgentLog';
import RiskTag from '@/components/RiskTag';
import { useTaskStore } from '@/store/taskStore';
import type { TaskEvent } from '@/types/task';

const mockLogs: TaskEvent[] = [
  { event_type: 'agent_log', timestamp: '2024-01-01T14:32:01Z', data: { message: '关键词生成完成 · 业务词46个 / 技术词29个 / 关联主体词38个' } },
  { event_type: 'agent_log', timestamp: '2024-01-01T14:38:17Z', data: { message: 'Fofa检索完成 · 返回资产2,104条 · 筛选后247条 (误判率11.2%)' } },
  { event_type: 'stage_progress', timestamp: '2024-01-01T14:52:44Z', data: { message: '接口爬取Agent启动 · 目标: admin.target.cn · 登录页识别成功', agent: 'APICRAWL-BROWSER' } },
  { event_type: 'stage_progress', timestamp: '2024-01-01T14:53:09Z', data: { message: '模拟登录操作 · 捕获POST /api/v2/auth/login · 参数: username/password/captcha', agent: 'APICRAWL-BROWSER' } },
  { event_type: 'vuln_found', timestamp: '2024-01-01T15:01:33Z', data: { message: '反爬检测触发 · 已切换IP代理 · 随机延迟注入 · 继续爬取' } },
  { event_type: 'stage_progress', timestamp: '2024-01-01T15:04:22Z', data: { message: '动态接口捕获 · GET /api/user/{id}/detail · 疑似越权参数', agent: 'APICRAWL-BROWSER' } },
  { event_type: 'agent_log', timestamp: '2024-01-01T15:11:58Z', data: { message: '接口特征库更新 · 已训练接口分类模型 · 操作类接口347个 / 查询类891个' } },
];

const Dashboard: React.FC = () => {
  const { currentTask, setCurrentTask } = useTaskStore();
  const [logs, setLogs] = useState<TaskEvent[]>(mockLogs);

  useEffect(() => {
    if (!currentTask) {
      getTask('task_01J9XXXXX').then(setCurrentTask).catch(console.error);
    }
  }, [currentTask, setCurrentTask]);

  if (!currentTask) return null;

  const { stats, stage_details } = currentTask;

  return (
    <div>
      <Row gutter={12} style={{ marginBottom: 20 }}>
        <Col span={6}><MetricCard title="发现资产数" value={stats.assets_found} delta="较传统方法 +70%" deltaType="up" /></Col>
        <Col span={6}><MetricCard title="接口爬取数" value={stats.interfaces_crawled} delta="漏爬率降至 8%" deltaType="up" /></Col>
        <Col span={6}><MetricCard title="检出漏洞" value={stats.vulns_detected} delta={`高危 ${12} / 中危 ${21}`} deltaType="down" /></Col>
        <Col span={6}><MetricCard title="探测进度" value={`${Math.round(currentTask.progress * 100)}%`} suffix="%" delta="预计剩余 4.2 小时" /></Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col span={12}>
          <Card title="五层流程 Agent 状态" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
            <AgentPipeline stageDetails={stage_details} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="高风险资产清单（部分）" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
            <Table
              size="small"
              pagination={false}
              dataSource={[
                { key: '1', asset: 'api.target.com', type: 'API网关', vuln: '未授权访问', risk: 'high' as const },
                { key: '2', asset: 'admin.target.cn', type: '管理后台', vuln: '越权操作', risk: 'high' as const },
                { key: '3', asset: 'search.target.com', type: '搜索接口', vuln: 'SQL注入', risk: 'high' as const },
                { key: '4', asset: 'upload.target.com', type: '文件服务', vuln: '恶意上传', risk: 'medium' as const },
                { key: '5', asset: 'h5.target.com', type: '移动端', vuln: 'XSS', risk: 'medium' as const },
                { key: '6', asset: 'static.target.com', type: '静态资源', vuln: '目录遍历', risk: 'low' as const },
              ]}
              columns={[
                { title: '资产', dataIndex: 'asset', key: 'asset' },
                { title: '类型', dataIndex: 'type', key: 'type' },
                { title: '漏洞', dataIndex: 'vuln', key: 'vuln' },
                { title: '风险', dataIndex: 'risk', key: 'risk', render: (risk: 'high' | 'medium' | 'low') => <RiskTag level={risk} /> },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="Agent 实时日志"
        size="small"
        style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Space>
            <Button size="small">暂停</Button>
            <Button size="small">导出报告</Button>
          </Space>
        }
      >
        <AgentLog events={logs} maxHeight={200} />
      </Card>
    </div>
  );
};

export default Dashboard;
```

- [ ] **Step 2: 提交**

```bash
git add web/src/pages/Dashboard/
git commit -m "feat: 添加 Dashboard 总览仪表盘页面"
```

---

## Task 11: Keywords + Assets 页面

**Files:**
- Create: `web/src/pages/Keywords/index.tsx`
- Create: `web/src/pages/Assets/index.tsx`

- [ ] **Step 1: 创建 Keywords 页面**

`web/src/pages/Keywords/index.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Input, Modal, Form, Select, Statistic, Row, Col, message } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { getKeywords, addKeyword, deleteKeyword } from '@/api/keywords';
import type { Keyword, KeywordType } from '@/types/keyword';

const typeColors: Record<KeywordType, string> = {
  business: '#378ADD',
  tech: '#BA7517',
  entity: '#534AB7',
};

const typeLabels: Record<KeywordType, string> = {
  business: '业务词',
  tech: '技术词',
  entity: '主体词',
};

const Keywords: React.FC = () => {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<KeywordType | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchKeywords = async () => {
    setLoading(true);
    try {
      const res = await getKeywords('task_01J9XXXXX', { type: filterType });
      setKeywords(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchKeywords(); }, [filterType]);

  const handleAdd = async (values: { word: string; type: KeywordType; weight: number }) => {
    await addKeyword('task_01J9XXXXX', { ...values, reason: '人工添加' });
    message.success('关键词已添加');
    setModalOpen(false);
    form.resetFields();
    fetchKeywords();
  };

  const handleDelete = async (id: string) => {
    await deleteKeyword('task_01J9XXXXX', id);
    message.success('已删除');
    fetchKeywords();
  };

  const businessCount = keywords.filter((k) => k.type === 'business').length;
  const techCount = keywords.filter((k) => k.type === 'tech').length;
  const entityCount = keywords.filter((k) => k.type === 'entity').length;

  return (
    <div>
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={8}><Card size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}><Statistic title={<span style={{ color: '#888' }}>业务词</span>} value={businessCount} valueStyle={{ color: typeColors.business }} /></Card></Col>
        <Col span={8}><Card size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}><Statistic title={<span style={{ color: '#888' }}>技术词</span>} value={techCount} valueStyle={{ color: typeColors.tech }} /></Card></Col>
        <Col span={8}><Card size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}><Statistic title={<span style={{ color: '#888' }}>主体词</span>} value={entityCount} valueStyle={{ color: typeColors.entity }} /></Card></Col>
      </Row>

      <Card
        title="关键词列表"
        size="small"
        style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Space>
            <Select
              placeholder="筛选类型"
              allowClear
              size="small"
              style={{ width: 120 }}
              value={filterType}
              onChange={setFilterType}
              options={[
                { value: 'business', label: '业务词' },
                { value: 'tech', label: '技术词' },
                { value: 'entity', label: '主体词' },
              ]}
            />
            <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>添加</Button>
          </Space>
        }
      >
        <Table
          size="small"
          loading={loading}
          dataSource={keywords}
          rowKey="id"
          pagination={{ pageSize: 20 }}
          columns={[
            { title: '关键词', dataIndex: 'word', key: 'word' },
            { title: '类型', dataIndex: 'type', key: 'type', render: (type: KeywordType) => <Tag color={typeColors[type]}>{typeLabels[type]}</Tag> },
            { title: '权重', dataIndex: 'weight', key: 'weight', render: (v: number) => v.toFixed(2), sorter: (a, b) => a.weight - b.weight },
            { title: '置信度', dataIndex: 'confidence', key: 'confidence', render: (v: number) => `${(v * 100).toFixed(0)}%` },
            { title: '来源', dataIndex: 'source', key: 'source', ellipsis: true },
            { title: '已用于DSL', dataIndex: 'used_in_dsl', key: 'used_in_dsl', render: (v: boolean) => v ? '是' : '否' },
            {
              title: '操作', key: 'action', render: (_, record) => (
                <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} />
              ),
            },
          ]}
        />
      </Card>

      <Modal title="添加关键词" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item name="word" label="关键词" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true }]}>
            <Select options={[{ value: 'business', label: '业务词' }, { value: 'tech', label: '技术词' }, { value: 'entity', label: '主体词' }]} />
          </Form.Item>
          <Form.Item name="weight" label="权重" initialValue={0.8} rules={[{ required: true }]}>
            <Input type="number" min={0} max={1} step={0.05} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Keywords;
```

- [ ] **Step 2: 创建 Assets 页面**

`web/src/pages/Assets/index.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { Card, Table, Select, Tag, Button, Drawer, Descriptions, Space } from 'antd';
import { ExportOutlined } from '@ant-design/icons';
import { getAssets } from '@/api/assets';
import RiskTag from '@/components/RiskTag';
import type { Asset, RiskLevel, AssetType } from '@/types/asset';

const Assets: React.FC = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [riskFilter, setRiskFilter] = useState<RiskLevel | undefined>();
  const [typeFilter, setTypeFilter] = useState<AssetType | undefined>();
  const [selected, setSelected] = useState<Asset | null>(null);

  const fetchAssets = async () => {
    setLoading(true);
    try {
      const res = await getAssets('task_01J9XXXXX', { risk: riskFilter, asset_type: typeFilter });
      setAssets(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAssets(); }, [riskFilter, typeFilter]);

  return (
    <div>
      <Card
        title="资产列表"
        size="small"
        style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Space>
            <Select placeholder="风险等级" allowClear size="small" style={{ width: 100 }} value={riskFilter} onChange={setRiskFilter}
              options={['critical', 'high', 'medium', 'low'].map((r) => ({ value: r, label: r }))} />
            <Select placeholder="资产类型" allowClear size="small" style={{ width: 100 }} value={typeFilter} onChange={setTypeFilter}
              options={['web', 'api', 'mobile', 'infra'].map((t) => ({ value: t, label: t }))} />
            <Button size="small" icon={<ExportOutlined />}>导出</Button>
          </Space>
        }
      >
        <Table
          size="small"
          loading={loading}
          dataSource={assets}
          rowKey="id"
          pagination={{ pageSize: 20 }}
          onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
          columns={[
            { title: '域名', dataIndex: 'domain', key: 'domain' },
            { title: 'IP', dataIndex: 'ip_address', key: 'ip_address' },
            { title: '类型', dataIndex: 'asset_type', key: 'asset_type', render: (v: string) => <Tag>{v}</Tag> },
            { title: '风险', dataIndex: 'risk_level', key: 'risk_level', render: (v: RiskLevel) => <RiskTag level={v} /> },
            { title: '接口数', dataIndex: 'interface_count', key: 'interface_count' },
            { title: '漏洞数', key: 'vuln_total', render: (_, r) => r.vuln_count.critical + r.vuln_count.high + r.vuln_count.medium + r.vuln_count.low },
            { title: 'ICP', dataIndex: 'icp_verified', key: 'icp', render: (v: boolean) => v ? <Tag color="green">已验证</Tag> : <Tag>未验证</Tag> },
          ]}
        />
      </Card>

      <Drawer title={selected?.domain} open={!!selected} onClose={() => setSelected(null)} width={520}>
        {selected && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="IP 地址">{selected.ip_address}</Descriptions.Item>
            <Descriptions.Item label="资产类型">{selected.asset_type}</Descriptions.Item>
            <Descriptions.Item label="风险等级"><RiskTag level={selected.risk_level} /></Descriptions.Item>
            <Descriptions.Item label="置信度">{(selected.confidence * 100).toFixed(0)}%</Descriptions.Item>
            <Descriptions.Item label="WAF">{selected.waf_detected || '未检测到'}</Descriptions.Item>
            <Descriptions.Item label="技术栈">{selected.tech_stack.join(', ')}</Descriptions.Item>
            <Descriptions.Item label="开放端口">{selected.open_ports.join(', ')}</Descriptions.Item>
            <Descriptions.Item label="接口数">{selected.interface_count}</Descriptions.Item>
            <Descriptions.Item label="漏洞统计">严重 {selected.vuln_count.critical} / 高危 {selected.vuln_count.high} / 中危 {selected.vuln_count.medium} / 低危 {selected.vuln_count.low}</Descriptions.Item>
            {selected.cert_info && <Descriptions.Item label="证书">颁发者: {selected.cert_info.issuer} · 过期: {selected.cert_info.expires_at}</Descriptions.Item>}
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default Assets;
```

- [ ] **Step 3: 提交**

```bash
git add web/src/pages/Keywords/ web/src/pages/Assets/
git commit -m "feat: 添加关键词生成 + 资产关联页面"
```

---

## Task 12: Interfaces + Pentest 页面

**Files:**
- Create: `web/src/pages/Interfaces/index.tsx`
- Create: `web/src/pages/Pentest/index.tsx`

- [ ] **Step 1: 创建 Interfaces 页面**

`web/src/pages/Interfaces/index.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { Card, Table, Tag, Select, Drawer, Descriptions, Input } from 'antd';
import { getInterfaces } from '@/api/interfaces';
import type { ApiInterface, ApiType, HttpMethod } from '@/types/interface';

const methodColors: Record<HttpMethod, string> = {
  GET: 'green', POST: 'blue', PUT: 'orange', PATCH: 'gold', DELETE: 'red',
};

const Interfaces: React.FC = () => {
  const [interfaces, setInterfaces] = useState<ApiInterface[]>([]);
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState<ApiType | undefined>();
  const [selected, setSelected] = useState<ApiInterface | null>(null);

  const fetchInterfaces = async () => {
    setLoading(true);
    try {
      const res = await getInterfaces('task_01J9XXXXX', { type: typeFilter });
      setInterfaces(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchInterfaces(); }, [typeFilter]);

  return (
    <div>
      <Card
        title="接口列表"
        size="small"
        style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Select placeholder="接口类型" allowClear size="small" style={{ width: 120 }} value={typeFilter} onChange={setTypeFilter}
            options={['query', 'operation', 'upload', 'search', 'auth', 'admin', 'other'].map((t) => ({ value: t, label: t }))} />
        }
      >
        <Table
          size="small"
          loading={loading}
          dataSource={interfaces}
          rowKey="id"
          pagination={{ pageSize: 20 }}
          onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
          columns={[
            { title: '方法', dataIndex: 'method', key: 'method', width: 80, render: (v: HttpMethod) => <Tag color={methodColors[v]}>{v}</Tag> },
            { title: '路径', dataIndex: 'path', key: 'path', ellipsis: true },
            { title: '类型', dataIndex: 'api_type', key: 'api_type', render: (v: string) => <Tag>{v}</Tag> },
            { title: '优先级', dataIndex: 'test_priority', key: 'priority', width: 70, sorter: (a, b) => a.test_priority - b.test_priority },
            { title: '权限敏感', dataIndex: 'privilege_sensitive', key: 'sensitive', width: 80, render: (v: boolean) => v ? <Tag color="red">是</Tag> : <Tag>否</Tag> },
            { title: '已测试', dataIndex: 'vuln_tested', key: 'tested', width: 70, render: (v: boolean) => v ? '是' : '否' },
            { title: '漏洞', dataIndex: 'vuln_count', key: 'vulns', width: 60 },
          ]}
        />
      </Card>

      <Drawer title={selected?.path} open={!!selected} onClose={() => setSelected(null)} width={600}>
        {selected && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="方法"><Tag color={methodColors[selected.method]}>{selected.method}</Tag></Descriptions.Item>
            <Descriptions.Item label="路径"><Input.TextArea value={selected.path} autoSize readOnly /></Descriptions.Item>
            <Descriptions.Item label="类型">{selected.api_type}</Descriptions.Item>
            <Descriptions.Item label="认证要求">{selected.auth_required ? '是' : '否'}</Descriptions.Item>
            <Descriptions.Item label="权限敏感">{selected.privilege_sensitive ? <Tag color="red">是</Tag> : '否'}</Descriptions.Item>
            <Descriptions.Item label="敏感参数">{selected.sensitive_params.join(', ') || '无'}</Descriptions.Item>
            <Descriptions.Item label="触发场景">{selected.trigger_scenario}</Descriptions.Item>
            <Descriptions.Item label="测试优先级">{selected.test_priority} / 10</Descriptions.Item>
            <Descriptions.Item label="爬取方式">{selected.crawl_method}</Descriptions.Item>
            <Descriptions.Item label="参数列表">
              {selected.parameters.length > 0 ? (
                <Table size="small" pagination={false} dataSource={selected.parameters} rowKey="name"
                  columns={[
                    { title: '名称', dataIndex: 'name' },
                    { title: '位置', dataIndex: 'location' },
                    { title: '类型', dataIndex: 'type' },
                    { title: '必填', dataIndex: 'required', render: (v: boolean) => v ? '是' : '否' },
                    { title: '敏感', dataIndex: 'sensitive', render: (v: boolean) => v ? <Tag color="red">是</Tag> : '否' },
                  ]}
                />
              ) : '无参数'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default Interfaces;
```

- [ ] **Step 2: 创建 Pentest 页面**

`web/src/pages/Pentest/index.tsx`:

```tsx
import { Card, Progress, Descriptions, Alert, Row, Col } from 'antd';
import StatusBadge from '@/components/StatusBadge';
import AgentLog from '@/components/AgentLog';
import { useTaskStore } from '@/store/taskStore';
import type { TaskEvent } from '@/types/task';

const mockPentestLogs: TaskEvent[] = [
  { event_type: 'stage_progress', timestamp: '2024-01-01T16:00:00Z', data: { message: '渗透测试等待接口爬取完成', stage: 'pentest' } },
  { event_type: 'stage_progress', timestamp: '2024-01-01T16:30:00Z', data: { message: '自动渗透 Agent 等待启动中...', stage: 'pentest' } },
];

const Pentest: React.FC = () => {
  const { currentTask } = useTaskStore();
  const pentestStage = currentTask?.stage_details.pentest;

  if (!currentTask) return null;

  const isRunning = pentestStage?.status === 'running';
  const isPending = pentestStage?.status === 'pending';

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Alert
            type={isRunning ? 'info' : isPending ? 'warning' : 'success'}
            message={isRunning ? '渗透测试运行中' : isPending ? '等待接口爬取完成' : '渗透测试已完成'}
            showIcon
            style={{ marginBottom: 16 }}
          />
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Card title="渗透测试状态" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="状态"><StatusBadge status={pentestStage?.status || 'pending'} /></Descriptions.Item>
              <Descriptions.Item label="当前阶段">自动渗透 Agent</Descriptions.Item>
              <Descriptions.Item label="配置强度">{currentTask.stage_details.pentest ? '标准' : '-'}</Descriptions.Item>
            </Descriptions>
            {pentestStage?.progress != null && (
              <Progress percent={Math.round(pentestStage.progress * 100)} style={{ marginTop: 12 }} strokeColor="#534AB7" />
            )}
          </Card>
        </Col>
        <Col span={16}>
          <Card title="实时日志" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
            <AgentLog events={mockPentestLogs} maxHeight={300} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Pentest;
```

- [ ] **Step 3: 提交**

```bash
git add web/src/pages/Interfaces/ web/src/pages/Pentest/
git commit -m "feat: 添加接口爬取 + 自动渗透页面"
```

---

## Task 13: Vulnerabilities + Reports 页面

**Files:**
- Create: `web/src/pages/Vulnerabilities/index.tsx`
- Create: `web/src/pages/Reports/index.tsx`

- [ ] **Step 1: 创建 Vulnerabilities 页面**

`web/src/pages/Vulnerabilities/index.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { Card, Table, Select, Drawer, Descriptions, Tag, Input, Progress } from 'antd';
import { getVulnerabilities } from '@/api/vulnerabilities';
import RiskTag from '@/components/RiskTag';
import type { Vulnerability, RiskLevel } from '@/types/vulnerability';

const VulnStatusTag: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = { confirmed: 'green', false_positive: 'default', fixed: 'blue', wont_fix: 'orange' };
  return <Tag color={colors[status] || 'default'}>{status}</Tag>;
};

const Vulnerabilities: React.FC = () => {
  const [vulns, setVulns] = useState<Vulnerability[]>([]);
  const [loading, setLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<RiskLevel | undefined>();
  const [selected, setSelected] = useState<Vulnerability | null>(null);

  const fetchVulns = async () => {
    setLoading(true);
    try {
      const res = await getVulnerabilities('task_01J9XXXXX', { severity: severityFilter });
      setVulns(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchVulns(); }, [severityFilter]);

  return (
    <div>
      <Card
        title="漏洞库"
        size="small"
        style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={
          <Select placeholder="严重性" allowClear size="small" style={{ width: 100 }} value={severityFilter} onChange={setSeverityFilter}
            options={['critical', 'high', 'medium', 'low'].map((s) => ({ value: s, label: s }))} />
        }
      >
        <Table
          size="small"
          loading={loading}
          dataSource={vulns}
          rowKey="id"
          pagination={{ pageSize: 20 }}
          onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: 'pointer' } })}
          columns={[
            { title: '漏洞标题', dataIndex: 'title', key: 'title', ellipsis: true },
            { title: '类型', dataIndex: 'vuln_type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
            { title: '严重性', dataIndex: 'severity', key: 'severity', width: 80, render: (v: RiskLevel) => <RiskTag level={v} /> },
            { title: 'CVSS', dataIndex: 'cvss_score', key: 'cvss', width: 60, sorter: (a, b) => a.cvss_score - b.cvss_score },
            { title: 'LLM置信度', key: 'confidence', width: 90, render: (_, r) => `${(r.llm_confidence * 100).toFixed(0)}%` },
            { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (v: string) => <VulnStatusTag status={v} /> },
            { title: '误报风险', dataIndex: 'false_positive_risk', key: 'fp', width: 80 },
          ]}
        />
      </Card>

      <Drawer title={selected?.title} open={!!selected} onClose={() => setSelected(null)} width={640}>
        {selected && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="漏洞类型">{selected.vuln_type}</Descriptions.Item>
            <Descriptions.Item label="严重性"><RiskTag level={selected.severity} /></Descriptions.Item>
            <Descriptions.Item label="CVSS 评分">{selected.cvss_score}</Descriptions.Item>
            <Descriptions.Item label="描述">{selected.description}</Descriptions.Item>
            <Descriptions.Item label="影响路径"><Input.TextArea value={selected.affected_path} autoSize readOnly /></Descriptions.Item>
            <Descriptions.Item label="测试载荷"><Input.TextArea value={selected.test_payload} autoSize readOnly /></Descriptions.Item>
            <Descriptions.Item label="LLM 置信度">
              <Progress percent={Math.round(selected.llm_confidence * 100)} size="small" style={{ width: 200 }} />
            </Descriptions.Item>
            <Descriptions.Item label="误报风险">{selected.false_positive_risk}</Descriptions.Item>
            <Descriptions.Item label="修复建议">{selected.remediation}</Descriptions.Item>
            <Descriptions.Item label="证据 — 请求"><Input.TextArea value={selected.evidence.request} autoSize readOnly style={{ fontFamily: 'monospace', fontSize: 12 }} /></Descriptions.Item>
            <Descriptions.Item label="证据 — 响应码">{selected.evidence.response_code}</Descriptions.Item>
            <Descriptions.Item label="证据 — 响应片段"><Input.TextArea value={selected.evidence.response_snippet} autoSize readOnly style={{ fontFamily: 'monospace', fontSize: 12 }} /></Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default Vulnerabilities;
```

- [ ] **Step 2: 创建 Reports 页面**

`web/src/pages/Reports/index.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, Progress, Modal, Form, Select, message } from 'antd';
import { DownloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { listReports, generateReport } from '@/api/reports';
import type { Report } from '@/api/reports';

const Reports: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [genModalOpen, setGenModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchReports = async () => {
    setLoading(true);
    try {
      const res = await listReports('task_01J9XXXXX');
      setReports(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchReports(); }, []);

  const handleGenerate = async (values: { template: string }) => {
    await generateReport('task_01J9XXXXX', {
      format: ['markdown', 'pdf'],
      sections: ['summary', 'assets', 'interfaces', 'vulns', 'remediation'],
      language: 'zh-CN',
      template: values.template as 'standard',
    });
    message.success('报告生成已触发');
    setGenModalOpen(false);
    form.resetFields();
    fetchReports();
  };

  return (
    <div>
      <Card
        title="报告中心"
        size="small"
        style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}
        extra={<Button size="small" type="primary" icon={<FileTextOutlined />} onClick={() => setGenModalOpen(true)}>生成报告</Button>}
      >
        <Table
          size="small"
          loading={loading}
          dataSource={reports}
          rowKey="report_id"
          pagination={{ pageSize: 20 }}
          columns={[
            { title: '报告 ID', dataIndex: 'report_id', key: 'id' },
            { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'completed' ? 'green' : 'blue'}>{v}</Tag> },
            { title: '质量评分', key: 'quality', render: (_, r) => r.quality_score ? <Progress percent={Math.round(r.quality_score.overall * 100)} size="small" style={{ width: 100 }} /> : '-' },
            { title: '页数', dataIndex: 'page_count', key: 'pages', width: 60 },
            { title: '字数', dataIndex: 'word_count', key: 'words', width: 80 },
            { title: '生成耗时', key: 'duration', width: 80, render: (_, r) => `${r.generation_duration_minutes} 分钟` },
            {
              title: '下载', key: 'download', render: (_, r) => (
                <span>
                  {r.files?.pdf && <Button size="small" type="link" icon={<DownloadOutlined />}>PDF</Button>}
                  {r.files?.markdown && <Button size="small" type="link" icon={<DownloadOutlined />}>MD</Button>}
                </span>
              ),
            },
          ]}
        />
      </Card>

      <Modal title="生成报告" open={genModalOpen} onCancel={() => setGenModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleGenerate}>
          <Form.Item name="template" label="报告模板" initialValue="standard" rules={[{ required: true }]}>
            <Select options={[
              { value: 'standard', label: '标准报告' },
              { value: 'detailed', label: '详细报告' },
              { value: 'executive', label: '高管摘要' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Reports;
```

- [ ] **Step 3: 提交**

```bash
git add web/src/pages/Vulnerabilities/ web/src/pages/Reports/
git commit -m "feat: 添加漏洞库 + 报告中心页面"
```

---

## Task 14: Settings 页面 + Hooks

**Files:**
- Create: `web/src/pages/Settings/index.tsx`
- Create: `web/src/hooks/useTaskEvents.ts`
- Create: `web/src/hooks/usePagination.ts`

- [ ] **Step 1: 创建 Settings 页面**

`web/src/pages/Settings/index.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { Card, Descriptions, Table, Tag, Form, InputNumber, Switch, Button, Row, Col, message } from 'antd';
import { getHealth, getMetrics, getAgentConfigs, updateAgentConfig } from '@/api/system';
import type { HealthResponse, MetricsResponse, AgentConfig } from '@/api/system';

const Settings: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [agents, setAgents] = useState<Record<string, AgentConfig>>({});

  useEffect(() => {
    getHealth().then(setHealth).catch(console.error);
    getMetrics().then(setMetrics).catch(console.error);
    getAgentConfigs().then(setAgents).catch(console.error);
  }, []);

  const handleUpdate = async (name: string, field: string, value: unknown) => {
    await updateAgentConfig(name, { [field]: value });
    message.success('配置已更新');
    getAgentConfigs().then(setAgents);
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="系统健康状态" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
            {health ? (
              <Descriptions column={2} size="small">
                {Object.entries(health.components).map(([key, val]) => (
                  <Descriptions.Item key={key} label={key}>
                    <Tag color={val.status === 'healthy' ? 'green' : 'red'}>{val.status}</Tag>
                    {val.latency_ms != null && <span style={{ color: '#888', fontSize: 11 }}>{val.latency_ms}ms</span>}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            ) : '加载中...'}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="系统指标" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
            {metrics ? (
              <Descriptions column={2} size="small">
                <Descriptions.Item label="活跃任务">{metrics.active_tasks}</Descriptions.Item>
                <Descriptions.Item label="队列任务">{metrics.queued_tasks}</Descriptions.Item>
                <Descriptions.Item label="今日完成">{metrics.completed_tasks_today}</Descriptions.Item>
                <Descriptions.Item label="平均耗时">{metrics.avg_task_duration_h}h</Descriptions.Item>
                <Descriptions.Item label="LLM 调用">{metrics.llm_calls_today}</Descriptions.Item>
                <Descriptions.Item label="LLM 费用">${metrics.llm_cost_usd_today}</Descriptions.Item>
                <Descriptions.Item label="今日发现资产">{metrics.assets_discovered_today}</Descriptions.Item>
                <Descriptions.Item label="今日确认漏洞">{metrics.vulns_confirmed_today}</Descriptions.Item>
              </Descriptions>
            ) : '加载中...'}
          </Card>
        </Col>
      </Row>

      <Card title="Agent 配置" size="small" style={{ background: '#1a1a2e', borderColor: '#2a2a4e' }}>
        <Table
          size="small"
          dataSource={Object.entries(agents).map(([name, config]) => ({ key: name, name, ...config }))}
          pagination={false}
          columns={[
            { title: 'Agent', dataIndex: 'name', key: 'name' },
            { title: '模型', dataIndex: 'model', key: 'model' },
            { title: 'Temperature', dataIndex: 'temperature', key: 'temp', width: 100 },
            { title: 'Max Tokens', dataIndex: 'max_tokens', key: 'tokens', width: 100 },
            { title: '超时(s)', dataIndex: 'timeout_s', key: 'timeout', width: 80 },
            { title: '重试', dataIndex: 'retry_attempts', key: 'retry', width: 60 },
            { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 70, render: (v: boolean, record) => <Switch size="small" checked={v} onChange={(val) => handleUpdate(record.name, 'enabled', val)} /> },
          ]}
        />
      </Card>
    </div>
  );
};

export default Settings;
```

- [ ] **Step 2: 创建 useTaskEvents hook**

`web/src/hooks/useTaskEvents.ts`:

```typescript
import { useEffect, useRef, useCallback } from 'react';
import { useTaskStore } from '@/store/taskStore';
import type { TaskEvent } from '@/types/task';

export function useTaskEvents(taskId: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null);
  const addEvent = useTaskStore((s) => s.addEvent);

  const connect = useCallback(() => {
    if (!taskId) return;

    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'ws://localhost:8000';
    const wsUrl = baseUrl.replace(/^http/, 'ws') + `/v1/tasks/${taskId}/events`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data: TaskEvent = JSON.parse(event.data);
        addEvent(data);
      } catch {
        // ignore non-JSON messages
      }
    };

    ws.onclose = () => {
      // reconnect after 3 seconds
      setTimeout(connect, 3000);
    };
  }, [taskId, addEvent]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const disconnect = () => {
    wsRef.current?.close();
    wsRef.current = null;
  };

  return { disconnect };
}
```

- [ ] **Step 3: 创建 usePagination hook**

`web/src/hooks/usePagination.ts`:

```typescript
import { useState } from 'react';

interface PaginationState {
  page: number;
  pageSize: number;
}

export function usePagination(defaultPageSize = 20) {
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    pageSize: defaultPageSize,
  });

  const onChange = (page: number, pageSize: number) => {
    setPagination({ page, pageSize });
  };

  return {
    page: pagination.page,
    pageSize: pagination.pageSize,
    onChange,
    reset: () => setPagination({ page: 1, pageSize: defaultPageSize }),
  };
}
```

- [ ] **Step 4: 提交**

```bash
git add web/src/pages/Settings/ web/src/hooks/
git commit -m "feat: 添加系统设置页面 + useTaskEvents/usePagination hooks"
```

---

## Task 15: 最终验证

- [ ] **Step 1: TypeScript 编译检查**

```bash
cd web && npx tsc --noEmit
```

预期：无错误。如有错误，逐个修复。

- [ ] **Step 2: 启动开发服务器**

```bash
cd web && npm run dev
```

预期：浏览器访问 http://localhost:3000 看到 AttackScope AI 界面，侧边栏可点击切换页面。

- [ ] **Step 3: 验证所有页面可访问**

逐个访问以下路由，确认页面正常渲染：
- `/` (Dashboard) — 指标卡片、Agent 管线、资产表、日志
- `/keywords` — 关键词表格、添加按钮
- `/assets` — 资产表格、筛选器、点击行打开 Drawer
- `/interfaces` — 接口表格、点击行打开 Drawer
- `/pentest` — 状态卡片、日志
- `/vulnerabilities` — 漏洞表格、点击行打开 Drawer
- `/reports` — 报告表格、生成按钮
- `/settings` — 健康状态、指标、Agent 配置表

- [ ] **Step 4: 最终提交**

```bash
git add web/
git commit -m "feat: 完成 AttackScope AI 前端框架搭建 (8页面 + 6共享组件 + Mock层)"
```

---

## 自查结果

**规范覆盖率：** 规范中每一节都有相应的任务。
- 技术栈 → 任务 1
- 项目结构 → 任务 1-14
- 路由设计 → 任务 9
- 页面/API映射 → 任务 10-14
- 共享组件 → 任务 8
- 数据流 → 任务 3, 5, 6
- Ant Design 主题 → 任务 9
- 实现边界 → 任务 1-14 (框架), 排除项未纳入

**占位符扫描：** 无 TBD、TODO 或 "后续实现" 占位符。所有代码完整。

**类型一致性：** 所有任务中引用的类型名称 (`RiskLevel`, `StageName`, `ApiInterface`, `TaskEvent` 等) 在任务 2 中定义，签名一致。
