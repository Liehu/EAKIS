import client from './client';
import type { AuditLogListResponse, AuditLogQueryParams } from '@/types/auditLog';

export const getAuditLogs = (params?: AuditLogQueryParams) =>
  client.get<AuditLogListResponse>('/v1/admin/audit-logs', { params }).then((r) => r.data);

export const getAuditLog = (logId: number) =>
  client.get(`/v1/admin/audit-logs/${logId}`).then((r) => r.data);
