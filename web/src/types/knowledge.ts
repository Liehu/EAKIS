// S3 知识库类型 — 对齐后端 routers/knowledge.py

export type KnowledgeStatus = 'draft' | 'pending_review' | 'published' | 'deprecated';

export type PayloadCategory = 'pass' | 'path' | 'user' | 'header' | 'payload' | 'keywords';

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

// ── 漏洞知识库 ────────────────────────────────────────────
export interface VulnKnowledge {
  id: string;
  name: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  vuln_id: string | null;
  vuln_type: string | null;
  vendor: string | null;
  product: string | null;
  version_range: string | null;
  affected_scope: string | null;
  fingerprint_id: string | null;
  poc: string | null;
  remediation: string | null;
  data_source: string | null;
  upstream_ref: string | null;
  status: KnowledgeStatus;
  contributed_by: string | null;
  reviewed_by: string | null;
  review_comment: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface VulnKnowledgeListParams {
  page?: number;
  page_size?: number;
  severity?: string;
  status?: string;
  vuln_type?: string;
  q?: string;
}

export interface VulnKnowledgeCreateRequest {
  name: string;
  severity: string;
  vuln_id?: string;
  vuln_type?: string;
  vendor?: string;
  product?: string;
  version_range?: string;
  affected_scope?: string;
  fingerprint_id?: string;
  poc?: string;
  remediation?: string;
  data_source?: string;
  upstream_ref?: string;
}

export interface ReviewRequest {
  action: 'submit' | 'approve' | 'reject' | 'deprecate';
  review_comment?: string;
}

// ── Payloads (字典/关键词合并) ───────────────────────────
export interface Payload {
  id: string;
  name: string | null;
  content: string;
  category: PayloadCategory;
  group_name: string | null;
  weight: number;
  hit_count: number;
  description: string | null;
  data_source: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface PayloadListParams {
  page?: number;
  page_size?: number;
  category?: PayloadCategory;
  group_name?: string;
  q?: string;
}

export interface PayloadCreateRequest {
  name?: string;
  content: string;
  category: PayloadCategory;
  group_name?: string;
  weight?: number;
  description?: string;
  data_source?: string;
}

export interface PayloadUpdateRequest {
  name?: string;
  content?: string;
  category?: PayloadCategory;
  group_name?: string;
  weight?: number;
  description?: string;
}

// ── 指纹库 ────────────────────────────────────────────────
export interface Fingerprint {
  id: string;
  name: string;
  category: string | null;
  component: string | null;
  version: string | null;
  match_type: string | null;
  match_rule: string;
  description: string | null;
  status: KnowledgeStatus;
  contributed_by: string | null;
  reviewed_by: string | null;
  tags: string[];
  vuln_count: number;
  created_at: string;
  updated_at: string;
}

export interface FingerprintCreateRequest {
  name: string;
  category?: string;
  component?: string;
  version?: string;
  match_type?: string;
  match_rule: string;
  description?: string;
  data_source?: string;
}

// ── 数据源 ────────────────────────────────────────────────
export interface Datasource {
  id: string;
  name: string;
  platform: string;
  api_base_url: string | null;
  config: string | null;
  description: string | null;
  is_active: number;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface DatasourceCreateRequest {
  name: string;
  platform: string;
  api_base_url?: string;
  config?: string;
  description?: string;
}

// ── 攻防手册 ──────────────────────────────────────────────
export interface Handbook {
  id: string;
  title: string;
  category: string | null;
  content: string;
  summary: string | null;
  status: KnowledgeStatus;
  contributed_by: string | null;
  reviewed_by: string | null;
  review_comment: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface HandbookCreateRequest {
  title: string;
  category?: string;
  content: string;
  summary?: string;
}

export interface ListResponse<T> {
  data: T[];
  pagination: Pagination;
}
