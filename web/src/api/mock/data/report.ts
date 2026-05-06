import type { Report } from '@/api/reports';

export const mockReports: Report[] = [
  {
    report_id: 'report_001',
    status: 'completed',
    quality_score: { overall: 0.93, accuracy: 0.96, completeness: 0.91, readability: 0.94, actionability: 0.89 },
    files: {
      markdown: 'https://storage.example.com/reports/rpt_001.md',
      pdf: 'https://storage.example.com/reports/rpt_001.pdf',
    },
    page_count: 47,
    word_count: 8234,
    generated_at: '2024-01-01T16:00:00Z',
    generation_duration_minutes: 18,
  },
];
