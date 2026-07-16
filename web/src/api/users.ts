import client from './client';
import type { UserListResponse, CreateUserRequest, UpdateUserRequest } from '@/types/user';

export const getUsers = (params?: { page?: number; page_size?: number; role?: string; is_active?: boolean }) =>
  client.get<UserListResponse>('/v1/admin/users', { params }).then((r) => r.data);

export const createUser = (data: CreateUserRequest) =>
  client.post('/v1/admin/users', data).then((r) => r.data);

export const getUser = (userId: string) =>
  client.get(`/v1/admin/users/${userId}`).then((r) => r.data);

export const updateUser = (userId: string, data: UpdateUserRequest) =>
  client.patch(`/v1/admin/users/${userId}`, data).then((r) => r.data);

export const deleteUser = (userId: string) =>
  client.delete(`/v1/admin/users/${userId}`);
