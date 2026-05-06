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
