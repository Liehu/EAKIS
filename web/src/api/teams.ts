import client from './client';
import type { TeamListResponse, CreateTeamRequest, UpdateTeamRequest, AddTeamMemberRequest, UpdateTeamMemberRoleRequest } from '@/types/team';

export const getTeams = (params?: { page?: number; page_size?: number }) =>
  client.get<TeamListResponse>('/v1/admin/teams', { params }).then((r) => r.data);

export const createTeam = (data: CreateTeamRequest) =>
  client.post('/v1/admin/teams', data).then((r) => r.data);

export const getTeam = (teamId: string) =>
  client.get(`/v1/admin/teams/${teamId}`).then((r) => r.data);

export const updateTeam = (teamId: string, data: UpdateTeamRequest) =>
  client.patch(`/v1/admin/teams/${teamId}`, data).then((r) => r.data);

export const deleteTeam = (teamId: string) =>
  client.delete(`/v1/admin/teams/${teamId}`);

export const addTeamMember = (teamId: string, data: AddTeamMemberRequest) =>
  client.post(`/v1/admin/teams/${teamId}/members`, data).then((r) => r.data);

export const updateTeamMemberRole = (teamId: string, userId: string, data: UpdateTeamMemberRoleRequest) =>
  client.patch(`/v1/admin/teams/${teamId}/members/${userId}`, data).then((r) => r.data);

export const removeTeamMember = (teamId: string, userId: string) =>
  client.delete(`/v1/admin/teams/${teamId}/members/${userId}`);
