import client from './client';
import type { Keyword, KeywordSummary, CreateKeywordRequest } from '@/types/keyword';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getKeywords = (taskId: string, params?: PaginationParams & { type?: string; min_weight?: number }) =>
  client.get<PaginatedResponse<Keyword> & { summary: KeywordSummary }>(`/v1/tasks/${taskId}/keywords`, { params }).then((r) => r.data);

export const addKeyword = (taskId: string, data: CreateKeywordRequest) =>
  client.post<Keyword>(`/v1/tasks/${taskId}/keywords`, data).then((r) => r.data);

export const deleteKeyword = (taskId: string, keywordId: string) =>
  client.delete(`/v1/tasks/${taskId}/keywords/${keywordId}`);

// 从任务情报文档生成关键词
export const generateKeywords = (taskId: string) =>
  client.post<PaginatedResponse<Keyword> & { summary: KeywordSummary }>(`/v1/tasks/${taskId}/keywords/generate`).then((r) => r.data);

// ── 企业关键词管理 ──────────────────────────────────────
export const getCompanyKeywords = (companyId: string, params?: PaginationParams & { type?: string; min_weight?: number }) =>
  client.get<PaginatedResponse<Keyword> & { summary: KeywordSummary }>(`/v1/companies/${companyId}/keywords`, { params }).then((r) => r.data);

export const addCompanyKeyword = (companyId: string, data: CreateKeywordRequest) =>
  client.post<Keyword>(`/v1/companies/${companyId}/keywords`, data).then((r) => r.data);

export const deleteCompanyKeyword = (companyId: string, keywordId: string) =>
  client.delete(`/v1/companies/${companyId}/keywords/${keywordId}`);

export const generateCompanyKeywords = (companyId: string) =>
  client.post<PaginatedResponse<Keyword> & { summary: KeywordSummary }>(`/v1/companies/${companyId}/keywords/generate`).then((r) => r.data);
