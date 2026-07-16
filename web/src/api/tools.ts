import client from './client';
import type { ToolInfo, RunToolRequest, ToolExecution, Pagination } from '@/types/tool';

// S5 工具管理 — 对齐后端 routers/tools.py
export const getTools = () =>
  client.get<ToolInfo[]>('/v1/tools').then((r) => r.data);

export const getTool = (name: string) =>
  client.get<ToolInfo>(`/v1/tools/${name}`).then((r) => r.data);

export const runTool = (toolName: string, data: RunToolRequest) =>
  client.post<ToolExecution>(`/v1/tools/${toolName}/run`, data).then((r) => r.data);

export const getToolStatus = (toolName: string) =>
  client.get<{ tool_name: string; last_status: string | null; last_run: string | null }>(`/v1/tools/${toolName}/status`).then((r) => r.data);

export const getToolExecutions = (params?: { tool_name?: string; task_id?: string; status?: string; page?: number; page_size?: number }) =>
  client.get<{ data: ToolExecution[]; pagination: Pagination }>('/v1/tool-executions', { params }).then((r) => r.data);

export const getToolExecution = (id: string) =>
  client.get<ToolExecution>(`/v1/tool-executions/${id}`).then((r) => r.data);
