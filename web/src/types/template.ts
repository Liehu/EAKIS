// S4 模板管理类型 — 对齐后端 routers/templates.py

export type TemplateType = 'task' | 'report' | 'prompt' | 'attack_path';
export type TemplateScope = 'org' | 'team' | 'private';

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

// 攻击路径 DAG
export interface DAGNode {
  id: string;
  type: string; // recon/vuln_scan/exploit/lateral/data_exfil
  label: string;
}
export interface DAGEdge {
  source: string;
  target: string;
  action: string; // auto/manual/conditional
}

// 类型专属 content
export interface TaskContent {
  target_depth?: number;
  holding_ratio_min?: number;
  include_minority?: boolean;
  modules?: string[];
  concurrency?: number;
  smart_c_segment?: boolean;
  smart_asset_link?: boolean;
  [k: string]: unknown;
}

export interface ReportContent {
  report_type: 'asset' | 'company' | 'vuln';
  fields: string[];
  layout?: string;
  format?: 'md' | 'html';
  cover?: boolean;
  toc?: boolean;
  [k: string]: unknown;
}

export interface PromptContent {
  agent: string;
  template: string;
  variables?: string[];
  source_file?: string;
  [k: string]: unknown;
}

export interface AttackPathContent {
  nodes: DAGNode[];
  edges: DAGEdge[];
  [k: string]: unknown;
}

export interface Template {
  id: string;
  org_id: string;
  name: string;
  template_type: TemplateType;
  description: string | null;
  content: Record<string, unknown>;
  parent_template_id: string | null;
  parent_name: string | null;
  scope: TemplateScope;
  owner_id: string | null;
  team_id: string | null;
  version: number;
  is_active: number;
  is_seed: number;
  created_at: string;
  updated_at: string;
}

export interface TemplateListParams {
  template_type?: TemplateType;
  scope?: TemplateScope;
  q?: string;
  page?: number;
  page_size?: number;
}

export interface TemplateCreateRequest {
  name: string;
  template_type: TemplateType;
  description?: string;
  content: Record<string, unknown>;
  parent_template_id?: string;
  scope?: TemplateScope;
  team_id?: string;
}

export interface TemplateUpdateRequest {
  name?: string;
  description?: string;
  content?: Record<string, unknown>;
  parent_template_id?: string | null;
  scope?: TemplateScope;
  team_id?: string | null;
  is_active?: number;
}

export interface ListResponse<T> {
  data: T[];
  pagination: Pagination;
}

export interface TemplateTypeInfo {
  value: TemplateType;
  label: string;
  description: string;
}
