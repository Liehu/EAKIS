import client from './client';
import type { Keyword, KeywordSummary, CreateKeywordRequest } from '@/types/keyword';
import type { PaginatedResponse, PaginationParams } from '@/types/api';

export const getKeywords = (taskId: string, params?: PaginationParams & { type?: string; min_weight?: number }) =>
  client.get<PaginatedResponse<Keyword> & { summary: KeywordSummary }>(`/v1/tasks/${taskId}/keywords`, { params }).then((r) => r.data);

export const addKeyword = (taskId: string, data: CreateKeywordRequest) =>
  client.post<Keyword>(`/v1/tasks/${taskId}/keywords`, data).then((r) => r.data);

export const deleteKeyword = (taskId: string, keywordId: string) =>
  client.delete(`/v1/tasks/${taskId}/keywords/${keywordId}`);
