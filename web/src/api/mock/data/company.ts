import type { Company } from '@/types/company';

export const mockCompanies: Company[] = [
  { id: 'comp_001', name: 'XX支付科技有限公司', aliases: ['XX支付', 'XX Pay'], industry: 'fintech', domains: ['xx-payment.com', 'xx-pay.cn'], ip_ranges: ['203.0.113.0/24'], exclude: ['mail.xx-payment.com'], task_count: 5, latest_task_status: 'running', created_at: '2024-01-01T00:00:00Z' },
  { id: 'comp_002', name: 'YY金融信息服务公司', aliases: ['YY金融', 'YY Fin'], industry: 'fintech', domains: ['yy-fin.com'], ip_ranges: ['198.51.100.0/24'], exclude: [], task_count: 3, latest_task_status: 'completed', created_at: '2024-01-15T00:00:00Z' },
  { id: 'comp_003', name: 'ZZ科技有限公司', aliases: ['ZZ科技'], industry: 'tech', domains: ['zz-tech.com', 'zz-tech.cn'], ip_ranges: ['192.0.2.0/24'], exclude: [], task_count: 1, latest_task_status: 'failed', created_at: '2024-02-01T00:00:00Z', notes: '某大型互联网公司' },
];
