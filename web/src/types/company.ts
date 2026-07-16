export interface Company {
  id: string;
  name: string;
  aliases: string[];
  industry: string;
  domains: string[];
  ip_ranges: string[];
  exclude: string[];
  task_count: number;
  latest_task_status: string | null;
  created_at: string;
  notes?: string;
  // S1 工商/业务字段 (后端 CompanyResponse 返回)
  credit_code?: string;
  business_status?: string;
  legal_person?: string;
  email_domains?: string[];
  work_id_rule?: string;
  keywords?: string[];
  website?: string;
  established_at?: string;
  registered_capital?: string;
  // S1 采集元信息 (后端 CompanyResponse 返回)
  data_source?: string | null;
  last_collected_at?: string | null;
}

export interface CreateCompanyRequest {
  name: string;
  aliases: string[];
  industry: string;
  domains: string[];
  ip_ranges: string[];
  exclude?: string[];
  notes?: string;
}

export interface SubCompany {
  id: string;
  name: string;
  full_name: string;
  credit_code: string;
  industry: string;
  keywords: string[];
  domains: string[];
  website: string | null;
  legal_person: string;
  status: string;
  work_id_rule: string;
  notes: string;
}

export interface OsintItem {
  id: string;
  title: string;
  source: string;
  date: string;
  summary: string;
}

export interface CompanyDetail {
  id: string;
  name: string;
  industry: string;
  status: string;
  credit_code: string;
  legal_person: string;
  work_id_rule: string;
  domains: string[];
  ip_ranges: string[];
  keywords: string[];
  notes: string;
  sub_company_count: number;
  latest_task_name: string | null;
  hierarchy_level: number;
  risk_count: number;
  sub_companies: SubCompany[];
  asset_summary: { total: number; by_type: Record<string, number> };
  vuln_summary: { total: number };
  osint_items: OsintItem[];
}

// ── S1 (A.1 企业关系穿透) ────────────────────────────────
export interface CompanyRelation {
  id: string;
  parent_company_id: string;
  child_company_id: string;
  relation_type: 'holding' | 'minority_stake' | 'branch' | 'historical';
  holding_ratio: number | null;
  data_source: string | null;
  created_at: string;
}

export interface GraphNode {
  id: string;
  name: string;
  type?: string;
  holding_ratio?: number | null;
  source?: string | null; // direct/inherited
  depth?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation_type: string;
  holding_ratio?: number | null;
}

export interface CompanyGraph {
  root_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ── S1 (A.7 风险评估) ────────────────────────────────────
export interface CompanyRisk {
  company_id: string;
  risk_score: number;
  asset_count: number;
  vuln_count: number;
  by_severity: { critical: number; high: number; medium: number; low: number; info?: number };
}

export interface RiskTrendPoint {
  snapshot_at: string;
  risk_score: number;
  asset_count: number;
  vuln_count: number;
}

export interface RiskTrend {
  company_id: string;
  points: RiskTrendPoint[];
}

// ── S1 (C.3 简称模糊匹配) ────────────────────────────────
export interface CompanySearchHit {
  id: string;
  name: string;
  aliases?: string[] | null;
  credit_code?: string | null;
  industry?: string | null;
}

// ── 企业主体采集 (商业 API: 云图/天眼查…) ──────────────────
export interface FieldConflict {
  field: string;
  old_value: unknown;
  new_value: unknown;
  old_source?: string | null;
  new_source?: string | null;
}

export interface EnrichRequest {
  provider?: string; // 默认 yuntu
  depth?: number;
  holding_min?: number;
  strategy?: 'auto_fill' | 'overwrite';
  recursive_depth?: number; // 0=不递归, 1=采集孙公司(三级), 2=更深层
}

export interface EnrichmentResponse {
  company_id: string;
  provider: string;
  fetched_at: string;
  updated_fields: string[];
  new_relations: number;
  conflicts: FieldConflict[];
  relations: CompanyRelation[];
}

export interface EnrichConfirmResolution {
  field: string;
  accepted_value: unknown;
}

export interface BatchEnrichRequest extends EnrichRequest {
  company_ids: string[];
}

export interface BatchEnrichItemResult {
  company_id: string;
  ok: boolean;
  error?: string | null;
  new_relations: number;
  conflicts: number;
}

export interface BatchEnrichResponse {
  results: BatchEnrichItemResult[];
  summary: { success: number; failed: number; total_relations: number };
}

// 企业详情聚合视图 (对齐后端 CompanyDetailResponse)
export interface CompanyDetailFull extends Company {
  sub_companies: SubCompany[];
  sub_company_count: number;
  hierarchy_level: number;
  asset_summary: { total: number; by_type: Record<string, number> };
  vuln_summary: { total: number; by_severity: Record<string, number> };
}
