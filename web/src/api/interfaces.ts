import client from './client';
import type { ApiInterface, InterfaceSummary, UpdateInterfaceRequest } from '@/types/interface';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getInterfaces = (taskId: string, params?: PaginationParams & {
  asset_id?: string;
  type?: string;
  privilege_sensitive?: boolean;
  auth_required?: boolean;
  min_priority?: number;
  method?: string;
}) =>
  client.get<PaginatedResponse<ApiInterface> & { summary: InterfaceSummary }>(`/v1/tasks/${taskId}/interfaces`, { params }).then((r) => r.data);

export const getInterface = (taskId: string, interfaceId: string) =>
  client.get<ApiInterface>(`/v1/tasks/${taskId}/interfaces/${interfaceId}`).then((r) => r.data);

export const updateInterface = (taskId: string, interfaceId: string, data: UpdateInterfaceRequest) =>
  client.patch<ApiInterface>(`/v1/tasks/${taskId}/interfaces/${interfaceId}`, data).then((r) => r.data);
