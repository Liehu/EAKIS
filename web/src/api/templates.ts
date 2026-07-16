import client from './client';
import type {
  Template, TemplateListParams, TemplateCreateRequest, TemplateUpdateRequest,
  ListResponse, TemplateTypeInfo,
} from '@/types/template';

export const getTemplates = (params?: TemplateListParams) =>
  client.get<ListResponse<Template>>('/v1/templates', { params }).then((r) => r.data);

export const getTemplate = (id: string) =>
  client.get<Template>(`/v1/templates/${id}`).then((r) => r.data);

export const createTemplate = (data: TemplateCreateRequest) =>
  client.post<Template>('/v1/templates', data).then((r) => r.data);

export const updateTemplate = (id: string, data: TemplateUpdateRequest) =>
  client.patch<Template>(`/v1/templates/${id}`, data).then((r) => r.data);

export const deleteTemplate = (id: string) =>
  client.delete(`/v1/templates/${id}`);

export const getTemplateTypes = () =>
  client.get<{ types: TemplateTypeInfo[] }>('/v1/templates/types').then((r) => r.data);
