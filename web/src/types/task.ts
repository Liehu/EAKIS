export type TaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
export type StageName = 'intelligence' | 'keyword_gen' | 'asset_discovery' | 'api_crawl' | 'pentest' | 'report_gen';
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface TaskStage {
  stage: StageName;
  status: StageStatus;
}

export interface CreateTaskRequest {
  company_name: string;
  company_aliases: string[];
  industry: string;
  authorized_scope: {
    domains: string[];
    ip_ranges: string[];
    exclude: string[];
  };
  config: {
    keyword_types: string[];
    asset_platforms: string[];
    crawl_depth: number;
    pentest_enabled: boolean;
    pentest_intensity: string;
    notification_webhook?: string;
  };
}

export interface TaskStats {
  assets_found: number;
  assets_confirmed: number;
  interfaces_crawled: number;
  vulns_detected: number;
  vulns_confirmed: number;
}

export interface StageDetail {
  status: StageStatus;
  duration_s?: number;
  items?: number;
  keywords?: number;
  assets?: number;
  confirmed?: number;
  progress?: number;
  interfaces?: number;
}

export interface Task {
  task_id: string;
  company_name: string;
  status: TaskStatus;
  current_stage: StageName | null;
  progress: number;
  stats: TaskStats;
  stage_details: Record<StageName, StageDetail>;
  created_at: string;
  started_at: string | null;
  estimated_completion: string | null;
  estimated_duration_hours?: number;
  stages?: TaskStage[];
}

export type TaskEventType = 'stage_progress' | 'agent_log' | 'vuln_found' | 'task_complete' | 'error';

export interface TaskEvent {
  event_type: TaskEventType;
  timestamp: string;
  data: {
    stage?: string;
    progress?: number;
    message: string;
    agent?: string;
  };
}
