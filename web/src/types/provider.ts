export type ProviderType = 'openai' | 'qwen' | 'zhipu' | 'ollama' | 'custom';

export interface AIProvider {
  id: string;
  name: string;
  type: ProviderType;
  api_key: string;
  base_url: string;
  enabled: boolean;
  created_at: string;
  models: string[];
}

export interface ModelAllocation {
  agent_name: string;
  provider_id: string;
  provider_name: string;
  model: string;
}

export interface ProviderUsage {
  provider_id: string;
  provider_name: string;
  total_calls: number;
  total_tokens: number;
  cost_usd: number;
  daily_usage: Array<{ date: string; calls: number; tokens: number; cost: number }>;
}

export interface CreateProviderRequest {
  name: string;
  type: ProviderType;
  api_key: string;
  base_url: string;
  models?: string[];
}
