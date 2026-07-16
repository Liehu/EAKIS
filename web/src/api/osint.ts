import client from './client';

// OSINT API - 开源情报（Stub）
export const getOsintDocuments = (taskId: string, params?: { page?: number; page_size?: number }) =>
  client.get(`/v1/tasks/${taskId}/intelligence/documents`, { params }).then((r) => r.data);

export const getCompanyOsint = (companyId: string, params?: { page?: number; page_size?: number }) =>
  client.get(`/v1/companies/${companyId}/osint`, { params }).then((r) => r.data);
