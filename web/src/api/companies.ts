import client from './client';
import type { Company, CreateCompanyRequest } from '@/types/company';
import type {
  CompanyRelation, CompanyGraph, CompanyRisk, RiskTrend, CompanySearchHit,
  EnrichRequest, EnrichmentResponse, EnrichConfirmResolution, BatchEnrichRequest,
  BatchEnrichResponse, CompanyDetailFull,
} from '@/types/company';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getCompanies = (params?: PaginationParams & { industry?: string; q?: string }) =>
  client.get<PaginatedResponse<Company>>('/v1/companies', { params }).then((r) => r.data);

export const getCompany = (id: string) =>
  client.get<Company>(`/v1/companies/${id}`).then((r) => r.data);

export const getCompanyDetail = (id: string): Promise<CompanyDetailFull> =>
  client.get<CompanyDetailFull>(`/v1/companies/${id}/detail`).then((r) => r.data);

export const createCompany = (
  data: CreateCompanyRequest,
  opts?: { enrich?: boolean; provider?: string },
) =>
  client
    .post<Company>('/v1/companies', data, {
      params: opts?.enrich ? { enrich: true, provider: opts.provider ?? 'yuntu' } : undefined,
    })
    .then((r) => r.data);

// PATCH — aligns with backend (S0 contract fix).
export const updateCompany = (id: string, data: Partial<CreateCompanyRequest>) =>
  client.patch<Company>(`/v1/companies/${id}`, data).then((r) => r.data);

export const deleteCompany = (id: string) =>
  client.delete(`/v1/companies/${id}`);

// ── S1 cascade queries (de-mock Companies/Detail) ────────
export const getCompanyAssets = (id: string, params?: PaginationParams & { asset_type?: string }) =>
  client.get<PaginatedResponse<unknown>>(`/v1/companies/${id}/assets`, { params }).then((r) => r.data);

export const getCompanyVulnerabilities = (id: string, params?: PaginationParams & { severity?: string }) =>
  client.get<PaginatedResponse<unknown>>(`/v1/companies/${id}/vulnerabilities`, { params }).then((r) => r.data);

// ── S1 relations (A.1) ───────────────────────────────────
export const getCompanyRelations = (
  id: string,
  params?: { direction?: 'children' | 'parents' | 'both'; relation_type?: string },
) =>
  client.get<CompanyRelation[]>(`/v1/companies/${id}/relations`, { params }).then((r) => r.data);

export const addCompanyRelation = (
  id: string,
  data: { parent_company_id: string; child_company_id: string; relation_type: string; holding_ratio?: number },
) =>
  client.post<CompanyRelation>(`/v1/companies/${id}/relations`, data).then((r) => r.data);

// ── S1 graph (A.1-决策6 ECharts) ─────────────────────────
export const getCompanyGraph = (
  id: string,
  params?: { depth?: number; holding_ratio_min?: number; include_minority?: boolean },
) =>
  client.get<CompanyGraph>(`/v1/companies/${id}/graph`, { params }).then((r) => r.data);

// ── S1 risk (A.7) ────────────────────────────────────────
export const getCompanyRisk = (id: string) =>
  client.get<CompanyRisk>(`/v1/companies/${id}/risk`).then((r) => r.data);

export const getCompanyRiskTrend = (id: string, limit = 30) =>
  client.get<RiskTrend>(`/v1/companies/${id}/risk/trend`, { params: { limit } }).then((r) => r.data);

// ── S1 search (C.3-决策4 简称模糊匹配) ───────────────────
export const searchCompanies = (q: string, limit = 10) =>
  client.get<{ query: string; hits: CompanySearchHit[] }>('/v1/companies/search', { params: { q, limit } }).then((r) => r.data);

// ── 企业主体采集 (商业 API: 云图/天眼查…) ──────────────────
export const listEnrichProviders = () =>
  client.get<string[]>('/v1/companies/enrich/providers').then((r) => r.data);

export const enrichCompany = (id: string, data: EnrichRequest = {}) =>
  client.post<EnrichmentResponse>(`/v1/companies/${id}/enrich`, data).then((r) => r.data);

export const confirmEnrichment = (id: string, resolutions: EnrichConfirmResolution[]) =>
  client
    .post<{ company_id: string; applied_fields: string[] }>(`/v1/companies/${id}/enrich/confirm`, { resolutions })
    .then((r) => r.data);

export const batchEnrich = (data: BatchEnrichRequest) =>
  client.post<BatchEnrichResponse>('/v1/companies/enrich/batch', data).then((r) => r.data);
