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

// Extended asset types for column definitions
export interface IPAsset extends Asset {
  fingerprints: string[];
  related_domains: string[];
  related_units: string[];
  source: string;
  is_cdn: boolean;
}

export interface DomainAsset extends Asset {
  resolve_records: Array<{ ip: string; port: number }>;
  related_units: string[];
  related_certs: Array<{ subject: string }>;
  icp_number: string;
  cloud_provider: string;
  is_cdn_wildcard: boolean;
}

export interface WebAsset extends Asset {
  url: string;
  title: string;
  icon: string;
  screenshot: string;
  related_units: string[];
}

export interface AppAsset extends Asset {
  name: string;
  related_units: string[];
  version: string;
  download_link: string;
}

export interface MiniProgramAsset extends Asset {
  name: string;
  related_units: string[];
  platform: string;
  access_link: string;
  is_internal: boolean;
  notes: string;
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

// ── 统一资产视图 (S1 资产多表 + 类型专属字段) ─────────────
// 对齐后端 TypedAssetItem (GET /v1/assets)

export type TypedAssetType = 'ip' | 'domain' | 'web' | 'app' | 'miniprogram' | 'certificate';

export interface TypedAsset {
  id: string;
  asset_type: TypedAssetType;
  domain: string | null;
  ip_address: string | null;
  port: number | null;
  risk_level: string;
  confidence: number;
  confirmed: boolean;
  company_id: string | null;
  company_name: string | null;
  tech_stack: string[];
  icp_entity: string | null;
  waf_type: string | null;
  status: string;
  source: string | null;
  notes: string | null;
  discovered_at: string | null;
  vuln_count: VulnCount;
  type_specific: Record<string, unknown>;
}

export interface TypedAssetListResponse {
  data: TypedAsset[];
  pagination: { page: number; page_size: number; total: number; total_pages: number };
}

export interface TypedAssetListParams {
  asset_type?: TypedAssetType;
  company_id?: string;
  risk?: string;
  confirmed?: boolean;
  q?: string;
  page?: number;
  page_size?: number;
}

export interface AssetFull {
  id: string;
  asset_type: string;
  domain: string | null;
  ip_address: string | null;
  port: number | null;
  risk_level: string;
  confirmed: boolean;
  company_id: string | null;
  company_name: string | null;
  tech_stack: string[];
  icp_entity: string | null;
  waf_type: string | null;
  open_ports: number[];
  cert_info: Record<string, unknown>;
  notes: string | null;
  status: string;
  value_score: number | null;
  discovered_at: string | null;
  type_specific: Record<string, unknown>;
  vulnerabilities: Array<{ id: string; title: string | null; severity: string; vuln_type: string | null; status: string | null }>;
}
