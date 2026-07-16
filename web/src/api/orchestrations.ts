import client from './client';

// Orchestration API - 任务编排（演练计划）（Stub）
export interface Orchestration {
  id: string;
  name: string;
  description?: string;
  status: 'draft' | 'running' | 'paused' | 'completed' | 'cancelled';
  created_by_user_id?: string;
  org_id?: string;
  task_count: number;
  progress: number;
  created_at: string;
  updated_at: string;
}

export interface OrchestrationTask {
  id: string;
  orchestration_id: string;
  task_id: string;
  sequence: number;
  name: string;
  status: string;
  progress: number;
}

export interface OrchestrationSummary {
  total_assets: number;
  total_vulns: number;
  total_interfaces: number;
}

export const createOrchestration = (data: { name: string; description?: string }) =>
  client.post('/v1/orchestrations', data).then((r) => r.data);

export const getOrchestrations = (params?: { page?: number; page_size?: number }) =>
  client.get('/v1/orchestrations', { params }).then((r) => r.data);

export const getOrchestration = (id: string) =>
  client.get(`/v1/orchestrations/${id}`).then((r) => r.data);

export const updateOrchestration = (id: string, data: Record<string, unknown>) =>
  client.patch(`/v1/orchestrations/${id}`, data).then((r) => r.data);

export const deleteOrchestration = (id: string) =>
  client.delete(`/v1/orchestrations/${id}`).then((r) => r.data);

export const addOrchestrationTask = (orchestrationId: string, data: { task_id: string; sequence?: number }) =>
  client.post(`/v1/orchestrations/${orchestrationId}/tasks`, data).then((r) => r.data);

export const getOrchestrationTasks = (orchestrationId: string) =>
  client.get(`/v1/orchestrations/${orchestrationId}/tasks`).then((r) => r.data);

export const removeOrchestrationTask = (orchestrationId: string, taskId: string) =>
  client.delete(`/v1/orchestrations/${orchestrationId}/tasks/${taskId}`).then((r) => r.data);

export const startOrchestration = (id: string) =>
  client.post(`/v1/orchestrations/${id}/start`).then((r) => r.data);

export const pauseOrchestration = (id: string) =>
  client.post(`/v1/orchestrations/${id}/pause`).then((r) => r.data);

export const resumeOrchestration = (id: string) =>
  client.post(`/v1/orchestrations/${id}/resume`).then((r) => r.data);

export const cancelOrchestration = (id: string) =>
  client.post(`/v1/orchestrations/${id}/cancel`).then((r) => r.data);

export const getOrchestrationSummary = (id: string) =>
  client.get(`/v1/orchestrations/${id}/summary`).then((r) => r.data);

export const generateOrchestrationReport = (id: string) =>
  client.post(`/v1/orchestrations/${id}/report`).then((r) => r.data);
