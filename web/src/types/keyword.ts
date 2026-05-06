export type KeywordType = 'business' | 'tech' | 'entity';

export interface Keyword {
  id: string;
  word: string;
  type: KeywordType;
  weight: number;
  confidence: number;
  source: string;
  derived: boolean;
  used_in_dsl: boolean;
}

export interface KeywordSummary {
  business_count: number;
  tech_count: number;
  entity_count: number;
  total: number;
}

export interface CreateKeywordRequest {
  word: string;
  type: KeywordType;
  weight: number;
  reason?: string;
}
