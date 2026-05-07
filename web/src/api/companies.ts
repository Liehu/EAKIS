import client from './client';
import type { Company, CreateCompanyRequest } from '@/types/company';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getCompanies = (params?: PaginationParams & { industry?: string }) =>
  client.get<PaginatedResponse<Company>>('/v1/companies', { params }).then((r) => r.data);

export const getCompany = (id: string) =>
  client.get<Company>(`/v1/companies/${id}`).then((r) => r.data);

export const createCompany = (data: CreateCompanyRequest) =>
  client.post<Company>('/v1/companies', data).then((r) => r.data);

export const updateCompany = (id: string, data: Partial<CreateCompanyRequest>) =>
  client.put<Company>(`/v1/companies/${id}`, data).then((r) => r.data);

export const deleteCompany = (id: string) =>
  client.delete(`/v1/companies/${id}`);
