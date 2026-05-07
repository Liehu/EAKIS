export type WebhookEventType = 'task.complete' | 'task.failed' | 'vuln.critical_found' | 'vuln.high_found' | 'stage.complete' | 'stage.failed';

export interface WebhookConfig {
  id: string;
  url: string;
  events: WebhookEventType[];
  secret: string;
  enabled: boolean;
  last_triggered_at: string | null;
  last_status: 'success' | 'failed' | null;
  failure_count: number;
  created_at: string;
}

export interface CreateWebhookRequest {
  url: string;
  events: WebhookEventType[];
  secret: string;
}
