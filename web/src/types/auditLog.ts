import type { PaginatedResponse } from './api';

export interface AuditLog {
  id: number;
  user_id?: string;
  username?: string;
  org_id?: string;
  team_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  ip_address?: string;
  user_agent?: string;
  request_method?: string;
  request_path?: string;
  status_code?: number;
  duration_ms?: number;
  detail?: Record<string, unknown>;
  created_at: string;
}

export type AuditLogListResponse = PaginatedResponse<AuditLog>;

export interface AuditLogQueryParams {
  page?: number;
  page_size?: number;
  user_id?: string;
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
}
