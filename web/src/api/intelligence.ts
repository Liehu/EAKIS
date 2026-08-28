import client from './client';

export interface IntelligenceStartRequest {
  company_name?: string;
  industry?: string;
  domains?: string[];
  keywords?: string[];
  enabled_categories?: string[];
  crawl_depth?: number;
}

// Intelligence API - M1 情报采集
// body 可为空 —— 后端会从 Task.company_id 自动取企业信息
export const startIntelligence = (taskId: string, data?: IntelligenceStartRequest) =>
  client.post(`/v1/tasks/${taskId}/intelligence`, data || {}).then((r) => r.data);

export const getIntelligenceStatus = (taskId: string) =>
  client.get(`/v1/tasks/${taskId}/intelligence`).then((r) => r.data);

export const getIntelligenceDocuments = (taskId: string, params?: { page?: number; page_size?: number }) =>
  client.get(`/v1/tasks/${taskId}/intelligence/documents`, { params }).then((r) => r.data);

export const getIntelligenceDsl = (taskId: string) =>
  client.get(`/v1/tasks/${taskId}/intelligence/dsl`).then((r) => r.data);

export const getIntelligenceSources = (taskId: string) =>
  client.get(`/v1/tasks/${taskId}/intelligence/sources`).then((r) => r.data);

export const ragSearch = (data: { query: string; top_k?: number; task_id?: string }) =>
  client.post('/v1/intelligence/rag/search', data).then((r) => r.data);

export const ragHealth = () =>
  client.get('/v1/intelligence/rag/health').then((r) => r.data);
