import client from './client';
import type { Vulnerability, VulnStatistics, UpdateVulnRequest } from '@/types/vulnerability';
import type { RiskLevel } from '@/types/asset';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getVulnerabilities = (taskId: string, params?: PaginationParams & {
  severity?: RiskLevel;
  vuln_type?: string;
  confirmed?: boolean;
  false_positive_risk?: string;
  asset_id?: string;
}) =>
  client.get<PaginatedResponse<Vulnerability> & { summary: VulnStatistics }>(`/v1/tasks/${taskId}/vulnerabilities`, { params }).then((r) => r.data);

export const getVulnerability = (taskId: string, vulnId: string) =>
  client.get<Vulnerability>(`/v1/tasks/${taskId}/vulnerabilities/${vulnId}`).then((r) => r.data);

export const updateVulnerability = (taskId: string, vulnId: string, data: UpdateVulnRequest) =>
  client.patch<Vulnerability>(`/v1/tasks/${taskId}/vulnerabilities/${vulnId}`, data).then((r) => r.data);

export const getVulnStatistics = (taskId: string) =>
  client.get<VulnStatistics>(`/v1/tasks/${taskId}/vulnerabilities/statistics`).then((r) => r.data);
