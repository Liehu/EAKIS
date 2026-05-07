import client from './client';
import type { Task, CreateTaskRequest } from '@/types/task';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const createTask = (data: CreateTaskRequest) =>
  client.post<Task>('/v1/tasks', data).then((r) => r.data);

export const getTask = (taskId: string) =>
  client.get<Task>(`/v1/tasks/${taskId}`).then((r) => r.data);

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
