export interface Company {
  id: string;
  name: string;
  aliases: string[];
  industry: string;
  domains: string[];
  ip_ranges: string[];
  exclude: string[];
  task_count: number;
  latest_task_status: string | null;
  created_at: string;
  notes?: string;
}

export interface CreateCompanyRequest {
  name: string;
  aliases: string[];
  industry: string;
  domains: string[];
  ip_ranges: string[];
  exclude?: string[];
  notes?: string;
}
