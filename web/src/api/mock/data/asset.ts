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

// Extended asset type with company association for Detail views
export interface CompanyAsset extends Asset {
  company_id: string;
  related_units?: string[];
  url?: string;
  name?: string;
}

export const mockIPAssets: CompanyAsset[] = [
  { ...mockAssets[0], company_id: 'comp_001', related_units: ['子公司A'] },
  { id: 'asset_007', domain: '', ip_address: '10.0.1.100', asset_type: 'api', confidence: 0.92, risk_level: 'medium',
    icp_verified: false, waf_detected: null, tech_stack: ['Java'], open_ports: [8080], cert_info: null,
    vuln_count: { critical: 0, high: 1, medium: 2, low: 0 }, interface_count: 15, discovered_at: '2024-01-02T10:00:00Z',
    company_id: 'comp_001', related_units: ['子公司A', '子公司B'] },
];

export const mockDomainAssets: CompanyAsset[] = [
  { ...mockAssets[1], company_id: 'comp_001', related_units: ['总部'] },
  { ...mockAssets[2], company_id: 'comp_001', related_units: ['总部'] },
  { id: 'asset_008', domain: 'pay.target.com', ip_address: '203.0.113.60', asset_type: 'web', confidence: 0.93, risk_level: 'high',
    icp_verified: true, waf_detected: null, tech_stack: ['Spring Boot', 'Nginx'], open_ports: [80, 443],
    cert_info: { subject: 'pay.target.com', issuer: "Let's Encrypt", expires_at: '2024-08-01' },
    vuln_count: { critical: 1, high: 2, medium: 3, low: 1 }, interface_count: 45, discovered_at: '2024-01-01T11:00:00Z',
    company_id: 'comp_001', related_units: ['支付中心'] },
];

export const mockWebAssets: CompanyAsset[] = [
  { ...mockAssets[3], company_id: 'comp_001', url: 'https://upload.target.com', related_units: ['总部'] },
  { ...mockAssets[4], company_id: 'comp_001', url: 'https://h5.target.com', related_units: ['移动端'] },
];

export const mockAppAssets: CompanyAsset[] = [
  { id: 'asset_009', domain: '', ip_address: '', asset_type: 'mobile', confidence: 0.90, risk_level: 'medium',
    icp_verified: false, waf_detected: null, tech_stack: ['Flutter', 'Dart'], open_ports: [],
    cert_info: null, vuln_count: { critical: 0, high: 1, medium: 1, low: 0 },
    interface_count: 30, discovered_at: '2024-01-03T09:00:00Z',
    company_id: 'comp_001', name: '安鉴APP', related_units: ['总部'] },
];

export const mockMiniProgramAssets: CompanyAsset[] = [
  { id: 'asset_010', domain: '', ip_address: '', asset_type: 'mobile', confidence: 0.88, risk_level: 'low',
    icp_verified: false, waf_detected: null, tech_stack: ['微信小程序'], open_ports: [],
    cert_info: null, vuln_count: { critical: 0, high: 0, medium: 1, low: 0 },
    interface_count: 18, discovered_at: '2024-01-04T09:00:00Z',
    company_id: 'comp_001', name: '安鉴小程序', related_units: ['移动端'] },
];
