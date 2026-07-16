// S5 工具管理类型 — 对齐后端 routers/tools.py

export interface ToolParamInfo {
  name: string;
  input_type: string; // domain/ip/cidr/url/word
  flag: string;
  required: boolean;
  multiple: boolean;
}

export interface ToolInfo {
  name: string;
  binary: string;
  description: string;
  category: string; // recon/dns/portscan/vulnscan/cert
  params: ToolParamInfo[];
  allowed_flags: string[];
  default_timeout: number;
  enabled: boolean;
}

export interface RunToolRequest {
  inputs: Record<string, string | string[]>;
  flags?: string[];
  timeout?: number;
  task_id?: string;
}

export interface ToolExecution {
  id: string;
  tool_name: string;
  category: string | null;
  task_id: string | null;
  inputs: Record<string, unknown>;
  flags: string[] | null;
  status: string; // success/failed/timeout/unavailable/invalid_input
  exit_code: number | null;
  stdout: string | null;
  stderr: string | null;
  parsed: unknown;
  duration_s: number | null;
  error: string | null;
  started_at: string;
  created_at: string;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}
