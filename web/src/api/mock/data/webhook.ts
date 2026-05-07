import type { WebhookConfig } from '@/types/webhook';

export const mockWebhooks: WebhookConfig[] = [
  { id: 'wh_001', url: 'https://hooks.slack.com/services/T00/B00/xxx', events: ['task.complete', 'vuln.critical_found'], secret: 'whsec_xxx', enabled: true, last_triggered_at: '2024-01-03T15:30:00Z', last_status: 'success', failure_count: 0, created_at: '2024-01-01T00:00:00Z' },
  { id: 'wh_002', url: 'https://hook.example.com/notify', events: ['task.complete', 'task.failed', 'stage.complete', 'stage.failed'], secret: 'whsec_yyy', enabled: true, last_triggered_at: '2024-01-03T14:20:00Z', last_status: 'success', failure_count: 1, created_at: '2024-01-02T00:00:00Z' },
  { id: 'wh_003', url: 'https://api.dingtalk.com/robot/send?access_token=xxx', events: ['vuln.critical_found'], secret: 'whsec_zzz', enabled: false, last_triggered_at: null, last_status: null, failure_count: 3, created_at: '2024-01-01T00:00:00Z' },
];
