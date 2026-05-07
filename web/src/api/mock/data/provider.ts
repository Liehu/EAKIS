import type { AIProvider, ModelAllocation, ProviderUsage } from '@/types/provider';

export const mockProviders: AIProvider[] = [
  { id: 'prov_001', name: '通义千问', type: 'qwen', api_key: 'sk-****xxxx', base_url: 'https://dashscope.aliyuncs.com/api/v1', enabled: true, created_at: '2024-01-01T00:00:00Z', models: ['qwen2.5-7b', 'qwen2.5-72b', 'qwen-max'] },
  { id: 'prov_002', name: 'OpenAI', type: 'openai', api_key: 'sk-****yyyy', base_url: 'https://api.openai.com/v1', enabled: true, created_at: '2024-01-01T00:00:00Z', models: ['gpt-4o', 'gpt-4o-mini'] },
  { id: 'prov_003', name: '本地 Ollama', type: 'ollama', api_key: '', base_url: 'http://localhost:11434', enabled: false, created_at: '2024-01-02T00:00:00Z', models: ['llama3:8b', 'codellama:13b'] },
];

export const mockModelAllocations: ModelAllocation[] = [
  { agent_name: 'KEYWORD-GEN', provider_id: 'prov_001', provider_name: '通义千问', model: 'qwen2.5-7b' },
  { agent_name: 'ASSET-DISCOVER', provider_id: 'prov_001', provider_name: '通义千问', model: 'qwen2.5-7b' },
  { agent_name: 'APICRAWL-BROWSER', provider_id: 'prov_002', provider_name: 'OpenAI', model: 'gpt-4o-mini' },
  { agent_name: 'PENTEST-AUTO', provider_id: 'prov_002', provider_name: 'OpenAI', model: 'gpt-4o' },
  { agent_name: 'REPORT-GEN', provider_id: 'prov_001', provider_name: '通义千问', model: 'qwen2.5-72b' },
];

export const mockProviderUsage: ProviderUsage[] = [
  {
    provider_id: 'prov_001', provider_name: '通义千问', total_calls: 3256, total_tokens: 4520000, cost_usd: 4.52,
    daily_usage: [
      { date: '2024-01-01', calls: 520, tokens: 780000, cost: 0.78 },
      { date: '2024-01-02', calls: 480, tokens: 650000, cost: 0.65 },
      { date: '2024-01-03', calls: 610, tokens: 890000, cost: 0.89 },
    ],
  },
  {
    provider_id: 'prov_002', provider_name: 'OpenAI', total_calls: 1565, total_tokens: 2100000, cost_usd: 7.95,
    daily_usage: [
      { date: '2024-01-01', calls: 230, tokens: 350000, cost: 1.20 },
      { date: '2024-01-02', calls: 280, tokens: 420000, cost: 1.50 },
      { date: '2024-01-03', calls: 310, tokens: 480000, cost: 1.75 },
    ],
  },
];
