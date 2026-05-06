import type { ApiInterface } from '@/types/interface';

export const mockInterfaces: ApiInterface[] = [
  {
    id: 'iface_001', asset_id: 'asset_001', path: '/api/v2/user/{userId}/orders', method: 'GET',
    api_type: 'query', parameters: [
      { name: 'userId', location: 'path', type: 'integer', required: true, sensitive: true },
      { name: 'page', location: 'query', type: 'integer', required: false, sensitive: false },
    ],
    auth_required: true, privilege_sensitive: true, sensitive_params: ['userId'],
    trigger_scenario: '点击订单列表', test_priority: 9, crawl_method: 'dynamic',
    vuln_tested: true, vuln_count: 2, version: 1, crawled_at: '2024-01-01T10:00:00Z',
  },
  {
    id: 'iface_002', asset_id: 'asset_001', path: '/api/v2/auth/login', method: 'POST',
    api_type: 'auth', parameters: [
      { name: 'username', location: 'body', type: 'string', required: true, sensitive: false },
      { name: 'password', location: 'body', type: 'string', required: true, sensitive: true },
      { name: 'captcha', location: 'body', type: 'string', required: true, sensitive: false },
    ],
    auth_required: false, privilege_sensitive: false, sensitive_params: ['password'],
    trigger_scenario: '登录操作', test_priority: 8, crawl_method: 'dynamic',
    vuln_tested: true, vuln_count: 1, version: 1, crawled_at: '2024-01-01T10:05:00Z',
  },
  {
    id: 'iface_003', asset_id: 'asset_002', path: '/admin/api/users', method: 'GET',
    api_type: 'admin', parameters: [
      { name: 'role', location: 'query', type: 'string', required: false, sensitive: false },
    ],
    auth_required: true, privilege_sensitive: true, sensitive_params: [],
    trigger_scenario: '管理员用户列表', test_priority: 10, crawl_method: 'dynamic',
    vuln_tested: true, vuln_count: 1, version: 1, crawled_at: '2024-01-01T10:10:00Z',
  },
  {
    id: 'iface_004', asset_id: 'asset_001', path: '/api/v2/transfer', method: 'POST',
    api_type: 'operation', parameters: [
      { name: 'to_account', location: 'body', type: 'string', required: true, sensitive: true },
      { name: 'amount', location: 'body', type: 'number', required: true, sensitive: true },
    ],
    auth_required: true, privilege_sensitive: true, sensitive_params: ['to_account', 'amount'],
    trigger_scenario: '转账操作', test_priority: 10, crawl_method: 'dynamic',
    vuln_tested: false, vuln_count: 0, version: 1, crawled_at: '2024-01-01T10:15:00Z',
  },
  {
    id: 'iface_005', asset_id: 'asset_003', path: '/search', method: 'GET',
    api_type: 'search', parameters: [
      { name: 'q', location: 'query', type: 'string', required: true, sensitive: false },
    ],
    auth_required: false, privilege_sensitive: false, sensitive_params: [],
    trigger_scenario: '搜索功能', test_priority: 7, crawl_method: 'static',
    vuln_tested: true, vuln_count: 1, version: 1, crawled_at: '2024-01-01T10:20:00Z',
  },
];
