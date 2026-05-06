export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
export type ApiType = 'query' | 'operation' | 'upload' | 'search' | 'auth' | 'admin' | 'other';

export interface InterfaceParam {
  name: string;
  location: 'path' | 'query' | 'header' | 'body';
  type: string;
  required: boolean;
  sensitive: boolean;
}

export interface ApiInterface {
  id: string;
  asset_id: string;
  path: string;
  method: HttpMethod;
  api_type: ApiType;
  parameters: InterfaceParam[];
  auth_required: boolean;
  privilege_sensitive: boolean;
  sensitive_params: string[];
  trigger_scenario: string;
  test_priority: number;
  crawl_method: 'dynamic' | 'static';
  vuln_tested: boolean;
  vuln_count: number;
  version: number;
  crawled_at: string;
}

export interface InterfaceSummary {
  total: number;
  by_type: Record<ApiType, number>;
  privilege_sensitive: number;
  untested: number;
}

export interface UpdateInterfaceRequest {
  test_priority?: number;
  notes?: string;
  skip_test?: boolean;
}
