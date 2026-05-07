import client from './client';
import type { WebhookConfig, CreateWebhookRequest } from '@/types/webhook';

export const getWebhooks = () =>
  client.get<{ data: WebhookConfig[] }>('/v1/config/webhooks').then((r) => r.data.data);

export const createWebhook = (data: CreateWebhookRequest) =>
  client.post<WebhookConfig>('/v1/config/webhooks', data).then((r) => r.data);

export const updateWebhook = (id: string, data: Partial<WebhookConfig>) =>
  client.put<WebhookConfig>(`/v1/config/webhooks/${id}`, data).then((r) => r.data);

export const deleteWebhook = (id: string) =>
  client.delete(`/v1/config/webhooks/${id}`);

export const testWebhook = (id: string) =>
  client.post<{ success: boolean; response_time_ms: number }>(`/v1/config/webhooks/${id}/test`).then((r) => r.data);
