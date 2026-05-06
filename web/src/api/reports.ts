import client from './client';
import type { PaginatedResponse } from '@/types/api';

export interface GenerateReportRequest {
  format: ('markdown' | 'pdf')[];
  sections: ('summary' | 'assets' | 'interfaces' | 'vulns' | 'remediation')[];
  language: string;
  template: 'standard' | 'detailed' | 'executive';
}

export interface ReportJob {
  report_job_id: string;
  status: string;
  estimated_minutes: number;
}

export interface Report {
  report_id: string;
  status: string;
  quality_score: {
    overall: number;
    accuracy: number;
    completeness: number;
    readability: number;
    actionability: number;
  };
  files: Record<string, string>;
  page_count: number;
  word_count: number;
  generated_at: string;
  generation_duration_minutes: number;
}

export const generateReport = (taskId: string, data: GenerateReportRequest) =>
  client.post<ReportJob>(`/v1/tasks/${taskId}/reports`, data).then((r) => r.data);

export const getReport = (taskId: string, reportId: string) =>
  client.get<Report>(`/v1/tasks/${taskId}/reports/${reportId}`).then((r) => r.data);

export const downloadReport = (taskId: string, reportId: string, format: 'pdf' | 'markdown') =>
  client.get(`/v1/tasks/${taskId}/reports/${reportId}/download`, { params: { format }, responseType: 'blob' });

export const listReports = (taskId: string) =>
  client.get<PaginatedResponse<Report>>(`/v1/tasks/${taskId}/reports`).then((r) => r.data);
