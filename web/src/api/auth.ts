import client from './client';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserInfo {
  id: string;
  org_id: string;
  email: string;
  display_name: string;
  phone: string | null;
  avatar_url: string | null;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
  role: string;
  permissions: string[];
  teams: Record<string, Record<string, string>>;
}

export const login = (data: LoginRequest) => {
  const params = new URLSearchParams();
  params.append('username', data.username);
  params.append('password', data.password);
  return client.post<LoginResponse>('/v1/auth/token', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  }).then((r) => r.data);
};

export const refreshAccessToken = (refreshToken: string) =>
  client.post<RefreshTokenResponse>('/v1/auth/refresh', { refresh_token: refreshToken })
    .then((r) => r.data);

export const logout = () =>
  client.post('/v1/auth/logout');

export const getMe = () =>
  client.get<UserInfo>('/v1/auth/me').then((r) => r.data);

export const changePassword = (data: { old_password: string; new_password: string }) =>
  client.patch('/v1/auth/me/password', data);

export interface InitAdminRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface SystemStatusResponse {
  initialized: boolean;
}

export const getSystemStatus = () =>
  client.get<SystemStatusResponse>('/v1/auth/system-status').then((r) => r.data);

export const initAdmin = (data: InitAdminRequest) =>
  client.post<LoginResponse>('/v1/auth/init-admin', data).then((r) => r.data);
