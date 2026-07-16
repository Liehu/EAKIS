import client from './client';
import type {
  VulnKnowledge, VulnKnowledgeListParams, VulnKnowledgeCreateRequest, ReviewRequest,
  Payload, PayloadListParams, PayloadCreateRequest, PayloadUpdateRequest,
  Fingerprint, FingerprintCreateRequest,
  Datasource, DatasourceCreateRequest,
  Handbook, HandbookCreateRequest,
  ListResponse,
} from '@/types/knowledge';

// ── 漏洞知识库 ────────────────────────────────────────────
export const getVulns = (params?: VulnKnowledgeListParams) =>
  client.get<ListResponse<VulnKnowledge>>('/v1/knowledge/vulns', { params }).then((r) => r.data);

export const getVuln = (id: string) =>
  client.get<VulnKnowledge>(`/v1/knowledge/vulns/${id}`).then((r) => r.data);

export const createVuln = (data: VulnKnowledgeCreateRequest) =>
  client.post<VulnKnowledge>('/v1/knowledge/vulns', data).then((r) => r.data);

export const updateVuln = (id: string, data: Partial<VulnKnowledgeCreateRequest>) =>
  client.patch<VulnKnowledge>(`/v1/knowledge/vulns/${id}`, data).then((r) => r.data);

export const deleteVuln = (id: string) =>
  client.delete(`/v1/knowledge/vulns/${id}`);

export const reviewVuln = (id: string, data: ReviewRequest) =>
  client.post<VulnKnowledge>(`/v1/knowledge/vulns/${id}/review`, data).then((r) => r.data);

// ── Payloads (字典/关键词合并) ───────────────────────────
export const getPayloads = (params?: PayloadListParams) =>
  client.get<ListResponse<Payload>>('/v1/knowledge/payloads', { params }).then((r) => r.data);

export const getPayload = (id: string) =>
  client.get<Payload>(`/v1/knowledge/payloads/${id}`).then((r) => r.data);

export const createPayload = (data: PayloadCreateRequest) =>
  client.post<Payload>('/v1/knowledge/payloads', data).then((r) => r.data);

export const updatePayload = (id: string, data: PayloadUpdateRequest) =>
  client.patch<Payload>(`/v1/knowledge/payloads/${id}`, data).then((r) => r.data);

export const deletePayload = (id: string) =>
  client.delete(`/v1/knowledge/payloads/${id}`);

export const recordPayloadHit = (id: string) =>
  client.post<Payload>(`/v1/knowledge/payloads/${id}/hit`).then((r) => r.data);

// ── 指纹库 ────────────────────────────────────────────────
export const getFingerprints = (params?: { page?: number; page_size?: number; category?: string; component?: string; q?: string }) =>
  client.get<ListResponse<Fingerprint>>('/v1/knowledge/fingerprints', { params }).then((r) => r.data);

export const getFingerprint = (id: string) =>
  client.get<Fingerprint>(`/v1/knowledge/fingerprints/${id}`).then((r) => r.data);

export const createFingerprint = (data: FingerprintCreateRequest) =>
  client.post<Fingerprint>('/v1/knowledge/fingerprints', data).then((r) => r.data);

export const updateFingerprint = (id: string, data: FingerprintCreateRequest) =>
  client.patch<Fingerprint>(`/v1/knowledge/fingerprints/${id}`, data).then((r) => r.data);

export const deleteFingerprint = (id: string) =>
  client.delete(`/v1/knowledge/fingerprints/${id}`);

// ── 数据源 ────────────────────────────────────────────────
export const getDatasources = (params?: { page?: number; page_size?: number; platform?: string }) =>
  client.get<ListResponse<Datasource>>('/v1/knowledge/datasources', { params }).then((r) => r.data);

export const createDatasource = (data: DatasourceCreateRequest) =>
  client.post<Datasource>('/v1/knowledge/datasources', data).then((r) => r.data);

export const updateDatasource = (id: string, data: DatasourceCreateRequest) =>
  client.patch<Datasource>(`/v1/knowledge/datasources/${id}`, data).then((r) => r.data);

export const deleteDatasource = (id: string) =>
  client.delete(`/v1/knowledge/datasources/${id}`);

// ── 攻防手册 ──────────────────────────────────────────────
export const getHandbooks = (params?: { page?: number; page_size?: number; category?: string; q?: string }) =>
  client.get<ListResponse<Handbook>>('/v1/knowledge/handbooks', { params }).then((r) => r.data);

export const getHandbook = (id: string) =>
  client.get<Handbook>(`/v1/knowledge/handbooks/${id}`).then((r) => r.data);

export const createHandbook = (data: HandbookCreateRequest) =>
  client.post<Handbook>('/v1/knowledge/handbooks', data).then((r) => r.data);

export const updateHandbook = (id: string, data: HandbookCreateRequest) =>
  client.patch<Handbook>(`/v1/knowledge/handbooks/${id}`, data).then((r) => r.data);

export const deleteHandbook = (id: string) =>
  client.delete(`/v1/knowledge/handbooks/${id}`);
