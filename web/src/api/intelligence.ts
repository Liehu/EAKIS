import client from './client';

// Intelligence API - M1 情报采集
export const startIntelligence = (taskId: string) =>
  client.post(`/v1/tasks/${taskId}/intelligence`).then((r) => r.data);

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
