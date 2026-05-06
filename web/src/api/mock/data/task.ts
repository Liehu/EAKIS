import type { Task } from '@/types/task';

export const mockTask: Task = {
  task_id: 'task_01J9XXXXX',
  company_name: '某金融科技公司',
  status: 'running',
  current_stage: 'api_crawl',
  progress: 0.68,
  stats: {
    assets_found: 247,
    assets_confirmed: 189,
    interfaces_crawled: 1832,
    vulns_detected: 43,
    vulns_confirmed: 31,
  },
  stage_details: {
    intelligence: { status: 'completed', duration_s: 180, items: 1250 },
    keyword_gen: { status: 'completed', keywords: 113 },
    asset_discovery: { status: 'completed', assets: 247, confirmed: 189 },
    api_crawl: { status: 'running', progress: 0.76, interfaces: 1832 },
    pentest: { status: 'pending' },
    report_gen: { status: 'pending' },
  },
  created_at: '2024-01-01T08:00:00Z',
  started_at: '2024-01-01T08:01:00Z',
  estimated_completion: '2024-01-01T16:00:00Z',
};

export const mockTasks: Task[] = [mockTask];
