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
