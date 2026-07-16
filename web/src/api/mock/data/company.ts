import type { Company, SubCompany, CompanyDetailFull, OsintItem } from '@/types/company';

export const mockCompanies: Company[] = [
  { id: 'comp_001', name: 'XX支付科技有限公司', aliases: ['XX支付', 'XX Pay'], industry: 'fintech', domains: ['xx-payment.com', 'xx-pay.cn'], ip_ranges: ['203.0.113.0/24'], exclude: ['mail.xx-payment.com'], task_count: 5, latest_task_status: 'running', created_at: '2024-01-01T00:00:00Z' },
  { id: 'comp_002', name: 'YY金融信息服务公司', aliases: ['YY金融', 'YY Fin'], industry: 'fintech', domains: ['yy-fin.com'], ip_ranges: ['198.51.100.0/24'], exclude: [], task_count: 3, latest_task_status: 'completed', created_at: '2024-01-15T00:00:00Z' },
  { id: 'comp_003', name: 'ZZ科技有限公司', aliases: ['ZZ科技'], industry: 'tech', domains: ['zz-tech.com', 'zz-tech.cn'], ip_ranges: ['192.0.2.0/24'], exclude: [], task_count: 1, latest_task_status: 'failed', created_at: '2024-02-01T00:00:00Z', notes: '某大型互联网公司' },
];

export const mockSubCompanies: (SubCompany & { parent_company_id: string })[] = [
  { id: 'sub_001', parent_company_id: 'comp_001', name: 'XX支付深圳分公司', full_name: 'XX支付科技有限公司深圳分公司', credit_code: '91440300MA5XXXXXX', industry: 'fintech', keywords: ['支付', '深圳'], domains: ['sz.xx-payment.com'], website: 'https://sz.xx-payment.com', legal_person: '张三', status: 'active', work_id_rule: 'SZ{4}', notes: '华南区运营中心' },
  { id: 'sub_002', parent_company_id: 'comp_001', name: 'XX数据服务有限公司', full_name: 'XX数据服务有限公司', credit_code: '91310000MA1YYYYYY', industry: 'data_security', keywords: ['数据安全', '云计算'], domains: ['data.xx-pay.cn'], website: 'https://data.xx-pay.cn', legal_person: '李四', status: 'active', work_id_rule: 'DATA{5}', notes: '数据处理子公司' },
  { id: 'sub_003', parent_company_id: 'comp_002', name: 'YY金融科技子公司', full_name: 'YY金融信息服务有限公司科技子公司', credit_code: '91110000MA2ZZZZZZ', industry: 'fintech', keywords: ['金融科技', '风控'], domains: ['tech.yy-fin.com'], website: null, legal_person: '王五', status: 'inactive', work_id_rule: '', notes: '' },
];

// mockOsint 保留供未来 OSINT 模块使用（详情页暂未展示真实数据）。
export const mockOsint: OsintItem[] = [
  { id: 'osint_001', title: 'XX支付完成B轮融资', source: '36氪', date: '2024-03-15', summary: 'XX支付科技宣布完成5亿元B轮融资，由红杉资本领投。' },
  { id: 'osint_002', title: 'XX支付被曝数据泄露', source: '安全客', date: '2024-02-20', summary: '安全研究人员发现XX支付某API接口存在未授权访问漏洞。' },
  { id: 'osint_003', title: 'XX支付获批支付牌照续期', source: '央行公告', date: '2024-01-10', summary: '中国人民银行公告批准XX支付科技有限公司支付业务许可证续期。' },
];

// 对齐后端 CompanyDetailResponse（Company 全字段 + 聚合视图）
export const mockCompanyDetails: Record<string, CompanyDetailFull> = {
  comp_001: {
    id: 'comp_001', name: 'XX支付科技有限公司', industry: 'fintech', aliases: ['XX支付', 'XX Pay'],
    domains: ['xx-payment.com', 'xx-pay.cn'], ip_ranges: ['203.0.113.0/24'], exclude: ['mail.xx-payment.com'],
    task_count: 5, latest_task_status: 'running', created_at: '2024-01-01T00:00:00Z',
    credit_code: '91440300MA5FXXXXX', business_status: '存续', legal_person: '赵六', work_id_rule: 'XX{6}',
    keywords: ['支付', '金融科技', '移动支付'], notes: '国内领先的第三方支付平台', data_source: 'yuntu',
    sub_company_count: 2, hierarchy_level: 2,
    sub_companies: mockSubCompanies.filter((s) => s.parent_company_id === 'comp_001').map(({ parent_company_id: _p, ...rest }) => rest),
    asset_summary: { total: 11, by_type: { ip: 2, domain: 3, web: 2, app: 1, miniprogram: 1 } },
    vuln_summary: { total: 8, by_severity: { critical: 1, high: 2, medium: 3, low: 2 } },
  },
  comp_002: {
    id: 'comp_002', name: 'YY金融信息服务公司', industry: 'fintech', aliases: ['YY金融', 'YY Fin'],
    domains: ['yy-fin.com'], ip_ranges: ['198.51.100.0/24'], exclude: [],
    task_count: 3, latest_task_status: 'completed', created_at: '2024-01-15T00:00:00Z',
    credit_code: '91310000MA1YYYYY', business_status: '存续', legal_person: '孙七', work_id_rule: '',
    keywords: ['金融', '信息服务'], notes: '', data_source: null,
    sub_company_count: 1, hierarchy_level: 2,
    sub_companies: mockSubCompanies.filter((s) => s.parent_company_id === 'comp_002').map(({ parent_company_id: _p, ...rest }) => rest),
    asset_summary: { total: 4, by_type: { ip: 1, domain: 1, web: 1, app: 1 } },
    vuln_summary: { total: 3, by_severity: { critical: 0, high: 1, medium: 1, low: 1 } },
  },
  comp_003: {
    id: 'comp_003', name: 'ZZ科技有限公司', industry: 'tech', aliases: ['ZZ科技'],
    domains: ['zz-tech.com', 'zz-tech.cn'], ip_ranges: ['192.0.2.0/24'], exclude: [],
    task_count: 1, latest_task_status: 'failed', created_at: '2024-02-01T00:00:00Z',
    credit_code: '91110000MA2ZZZZZ', business_status: '存续', legal_person: '周八', work_id_rule: '',
    keywords: ['科技', '互联网'], notes: '某大型互联网公司', data_source: null,
    sub_company_count: 0, hierarchy_level: 1,
    sub_companies: [],
    asset_summary: { total: 2, by_type: { ip: 1, domain: 1 } },
    vuln_summary: { total: 1, by_severity: { critical: 0, high: 0, medium: 1, low: 0 } },
  },
};
