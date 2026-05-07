import client from './client';
import type { AIProvider, ModelAllocation, ProviderUsage, CreateProviderRequest } from '@/types/provider';

export const getProviders = () =>
  client.get<{ data: AIProvider[] }>('/v1/config/providers').then((r) => r.data.data);

export const getProvider = (id: string) =>
  client.get<AIProvider>(`/v1/config/providers/${id}`).then((r) => r.data);

export const createProvider = (data: CreateProviderRequest) =>
  client.post<AIProvider>('/v1/config/providers', data).then((r) => r.data);

export const updateProvider = (id: string, data: Partial<AIProvider>) =>
  client.put<AIProvider>(`/v1/config/providers/${id}`, data).then((r) => r.data);

export const deleteProvider = (id: string) =>
  client.delete(`/v1/config/providers/${id}`);

export const getModelAllocations = () =>
  client.get<ModelAllocation[]>('/v1/config/model-allocations').then((r) => r.data);

export const updateModelAllocation = (agentName: string, data: { provider_id: string; model: string }) =>
  client.put(`/v1/config/model-allocations/${agentName}`, data).then((r) => r.data);

export const getProviderUsage = (providerId?: string) =>
  client.get<ProviderUsage[]>('/v1/config/providers/usage', { params: { provider_id: providerId } }).then((r) => r.data);
