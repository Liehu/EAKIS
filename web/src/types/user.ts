import type { PaginatedResponse } from './api';

export type UserRole = 'super_admin' | 'org_admin' | 'team_lead' | 'engineer' | 'analyst' | 'auditor';

export interface User {
  id: string;
  org_id: string;
  email: string;
  display_name: string;
  phone?: string;
  avatar_url?: string;
  is_active: boolean;
  last_login_at?: string;
  created_at: string;
  updated_at: string;
}

export type UserListResponse = PaginatedResponse<User>;

export interface CreateUserRequest {
  email: string;
  password: string;
  display_name: string;
  phone?: string;
  role_name: UserRole;
  team_ids?: string[];
}

export interface UpdateUserRequest {
  display_name?: string;
  phone?: string;
  avatar_url?: string;
  is_active?: boolean;
}
