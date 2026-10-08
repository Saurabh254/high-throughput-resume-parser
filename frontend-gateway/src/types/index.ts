export interface CandidateMetadata {
  full_name?: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedin_url?: string;
  github_url?: string;
}

export interface ImpactMetric {
  metric_type: string;
  raw_statement: string;
  quantified_value?: string;
}

export interface WorkExperienceItem {
  company: string;
  job_title: string;
  standardized_role?: string;
  seniority_level?: string;
  start_date?: string;
  end_date?: string;
  duration_months: number;
  is_current: boolean;
  technologies_used: string[];
  impact_metrics: ImpactMetric[];
  experience_narrative: string;
  order_index: number;
}

export interface EducationItem {
  institution: string;
  degree?: string;
  field_of_study?: string;
  graduation_year?: string;
}

export interface CandidateProfile {
  metadata: CandidateMetadata;
  total_years_experience: number;
  work_experiences: WorkExperienceItem[];
  education: EducationItem[];
  core_skills: string[];
  experience_summary: string;
  raw_text: string;
  file_hash: string;
  filename: string;
}

export interface ScoreBreakdown {
  cosine_similarity: number;
  bert_rerank_score: number;
  experience_depth_score: number;
  composite_score: number;
}

export interface SearchCandidateResult {
  candidate_id: string;
  file_hash: string;
  filename: string;
  full_name: string;
  email?: string;
  location?: string;
  total_years_experience: number;
  current_role?: string;
  current_company?: string;
  score_breakdown: ScoreBreakdown;
  experience_highlights: string[];
  matched_skills: string[];
  work_experiences: WorkExperienceItem[];
}

export interface SearchResponse {
  query_time_ms: number;
  cache_hit: boolean;
  total_matches: number;
  results: SearchCandidateResult[];
}

export interface SystemStats {
  status: string;
  total_candidates: number;
  total_work_experiences: number;
  total_embeddings: number;
  embedding_dimensions: number;
  embedding_model: string;
  reranker_model: string;
}
