import client from './client';
import type { Asset, AssetListParams, UpdateAssetRequest } from '@/types/asset';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export interface DiscoverAssetsRequest {
  dsl_queries: Array<{ platform: string; query: string }>;
  company_name?: string;
  target_domains?: string[];
  target_icp_entity?: string;
  target_ip_ranges?: string[];
}

export interface DiscoverAssetsResponse {
  task_id: string;
  status: string;
  total_searched: number;
  total_candidates: number;
  total_confirmed: number;
  total_enriched: number;
  by_asset_type: Record<string, number>;
  avg_confidence: number;
  errors: string[];
}

export interface AssetDiscoveryStatus {
  task_id: string;
  status: string;
  total_assets: number;
  total_confirmed: number;
  by_asset_type: Record<string, number>;
  avg_confidence: number;
}

export const getAssets = (taskId: string, params?: PaginationParams & AssetListParams) =>
  client.get<PaginatedResponse<Asset>>(`/v1/tasks/${taskId}/assets`, { params }).then((r) => r.data);

export const getAsset = (taskId: string, assetId: string) =>
  client.get<Asset>(`/v1/tasks/${taskId}/assets/${assetId}`).then((r) => r.data);

export const updateAsset = (taskId: string, assetId: string, data: UpdateAssetRequest) =>
  client.patch<Asset>(`/v1/tasks/${taskId}/assets/${assetId}`, data).then((r) => r.data);

export const discoverAssets = (taskId: string, data: DiscoverAssetsRequest) =>
  client.post<DiscoverAssetsResponse>(`/v1/tasks/${taskId}/assets/discover`, data).then((r) => r.data);

export const getAssetDiscoverStatus = (taskId: string) =>
  client.get<AssetDiscoveryStatus>(`/v1/tasks/${taskId}/assets/status`).then((r) => r.data);

export const exportAssets = (taskId: string, format: 'csv' | 'xlsx' | 'json') =>
  client.get(`/v1/tasks/${taskId}/assets/export`, { params: { format }, responseType: 'blob' });

// ── S1 统一资产视图 (全局, 按类型 + 类型专属字段) ─────────
import type { TypedAssetListResponse, TypedAssetListParams, AssetFull } from '@/types/asset';

export const getTypedAssets = (params?: TypedAssetListParams) =>
  client.get<TypedAssetListResponse>('/v1/assets', { params }).then((r) => r.data);

export const getAssetFull = (assetId: string) =>
  client.get<AssetFull>(`/v1/assets/${assetId}/full`).then((r) => r.data);
