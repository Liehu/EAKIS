import client from './client';
import type { ApiInterface, InterfaceSummary, UpdateInterfaceRequest } from '@/types/interface';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export interface CrawlInterfacesRequest {
  assets: Array<{ asset_id: string; url: string }>;
}

export interface CrawlInterfacesResponse {
  task_id: string;
  status: string;
  total_assets: number;
  total_raw: number;
  total_classified: number;
  by_type: Record<string, number>;
  privilege_sensitive_count: number;
  errors: string[];
}

export interface InterfaceCrawlStatus {
  task_id: string;
  status: string;
  total_interfaces: number;
  by_type: Record<string, number>;
  privilege_sensitive_count: number;
}

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

export const crawlInterfaces = (taskId: string, data: CrawlInterfacesRequest) =>
  client.post<CrawlInterfacesResponse>(`/v1/tasks/${taskId}/interfaces/crawl`, data).then((r) => r.data);

export const getInterfaceCrawlStatus = (taskId: string) =>
  client.get<InterfaceCrawlStatus>(`/v1/tasks/${taskId}/interfaces/status`).then((r) => r.data);
