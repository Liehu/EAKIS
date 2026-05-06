import client from './client';

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  components: Record<string, { status: string; latency_ms?: number; lag?: number; pool_size?: number }>;
}

export interface MetricsResponse {
  active_tasks: number;
  queued_tasks: number;
  completed_tasks_today: number;
  avg_task_duration_h: number;
  llm_calls_today: number;
  llm_cost_usd_today: number;
  assets_discovered_today: number;
  vulns_confirmed_today: number;
  api_requests_per_min: number;
}

export interface AgentConfig {
  model: string;
  temperature: number;
  max_tokens: number;
  timeout_s: number;
  retry_attempts: number;
  enabled: boolean;
}

export const getHealth = () =>
  client.get<HealthResponse>('/v1/health').then((r) => r.data);

export const getMetrics = () =>
  client.get<MetricsResponse>('/v1/metrics').then((r) => r.data);

export const getAgentConfigs = () =>
  client.get<Record<string, AgentConfig>>('/v1/config/agents').then((r) => r.data);

export const getAgentConfig = (agentName: string) =>
  client.get<AgentConfig>(`/v1/config/agents/${agentName}`).then((r) => r.data);

export const updateAgentConfig = (agentName: string, data: Partial<AgentConfig>) =>
  client.put<AgentConfig>(`/v1/config/agents/${agentName}`, data).then((r) => r.data);
