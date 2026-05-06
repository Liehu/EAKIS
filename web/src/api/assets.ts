import client from './client';
import type { Asset, AssetListParams, UpdateAssetRequest } from '@/types/asset';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getAssets = (taskId: string, params?: PaginationParams & AssetListParams) =>
  client.get<PaginatedResponse<Asset>>(`/v1/tasks/${taskId}/assets`, { params }).then((r) => r.data);

export const getAsset = (taskId: string, assetId: string) =>
  client.get<Asset>(`/v1/tasks/${taskId}/assets/${assetId}`).then((r) => r.data);

export const updateAsset = (taskId: string, assetId: string, data: UpdateAssetRequest) =>
  client.patch<Asset>(`/v1/tasks/${taskId}/assets/${assetId}`, data).then((r) => r.data);

export const exportAssets = (taskId: string, format: 'csv' | 'xlsx' | 'json') =>
  client.get(`/v1/tasks/${taskId}/assets/export`, { params: { format }, responseType: 'blob' });
