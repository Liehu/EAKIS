import type { PaginatedResponse } from './api';

export type TeamRole = 'super_admin' | 'org_admin' | 'team_lead' | 'engineer' | 'analyst' | 'auditor';

export interface TeamMember {
  user_id: string;
  team_id: string;
  role_name: string;
  display_name: string;
  email: string;
  joined_at: string;
  invited_by?: string;
}

export interface Team {
  id: string;
  org_id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  member_count: number;
}

export interface TeamDetail extends Team {
  members: TeamMember[];
}

export type TeamListResponse = PaginatedResponse<Team>;

export interface CreateTeamRequest {
  name: string;
  description?: string;
}

export interface UpdateTeamRequest {
  name?: string;
  description?: string;
}

export interface AddTeamMemberRequest {
  user_id: string;
  role_name: TeamRole;
}

export interface UpdateTeamMemberRoleRequest {
  role_name: TeamRole;
}
