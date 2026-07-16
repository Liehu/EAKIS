import client from './client';
import type { Task, CreateTaskRequest } from '@/types/task';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  current_stage: string | null;
  progress: number;
  error_message: string | null;
}

export interface UpdateTaskRequest {
  company_name?: string;
  company_aliases?: string[];
  industry?: string;
  status?: string;
  current_stage?: string;
  progress?: number;
  config?: Record<string, unknown>;
  error_message?: string;
  authorized_scope?: Record<string, unknown>;
}

export const createTask = (data: CreateTaskRequest) =>
  client.post<Task>('/v1/tasks', data).then((r) => r.data);

export const getTask = (taskId: string) =>
  client.get<Task>(`/v1/tasks/${taskId}`).then((r) => r.data);

export const updateTask = (taskId: string, data: UpdateTaskRequest) =>
  client.put<Task>(`/v1/tasks/${taskId}`, data).then((r) => r.data);

export const deleteTask = (taskId: string) =>
  client.delete(`/v1/tasks/${taskId}`);

export const getTaskStatus = (taskId: string) =>
  client.get<TaskStatusResponse>(`/v1/tasks/${taskId}/status`).then((r) => r.data);

export const listTasks = (params?: PaginationParams & { status?: string }) =>
  client.get<PaginatedResponse<Task>>('/v1/tasks', { params }).then((r) => r.data);

export const pauseTask = (taskId: string) =>
  client.post(`/v1/tasks/${taskId}/pause`);

export const resumeTask = (taskId: string) =>
  client.post(`/v1/tasks/${taskId}/resume`);

export const cancelTask = (taskId: string) =>
  client.post(`/v1/tasks/${taskId}/cancel`);

export const retryTask = (taskId: string) =>
  client.post(`/v1/tasks/${taskId}/retry`);

export const batchCancelTasks = (taskIds: string[]) =>
  client.post('/v1/tasks/batch/cancel', { task_ids: taskIds });

export const batchResumeTasks = (taskIds: string[]) =>
  client.post('/v1/tasks/batch/resume', { task_ids: taskIds });
