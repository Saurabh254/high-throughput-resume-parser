from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class CandidateMetadata(BaseModel):
    full_name: Optional[str] = "Unknown Candidate"
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None

class ImpactMetric(BaseModel):
    metric_type: str = "general" # percentage, scale, latency, team_size, revenue
    raw_statement: str
    quantified_value: Optional[str] = None

class WorkExperienceItem(BaseModel):
    company: str
    job_title: str
    standardized_role: Optional[str] = "Software Engineer"
    seniority_level: Optional[str] = "Mid"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_months: int = 0
    is_current: bool = False
    technologies_used: List[str] = Field(default_factory=list)
    impact_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    experience_narrative: str
    order_index: int = 0

class EducationItem(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[str] = None

class CandidateProfile(BaseModel):
    metadata: CandidateMetadata = Field(default_factory=CandidateMetadata)
    total_years_experience: float = 0.0
    work_experiences: List[WorkExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    core_skills: List[str] = Field(default_factory=list)
    experience_summary: str = ""
    raw_text: str = ""
    file_hash: str = ""
    filename: str = ""

class SearchRequest(BaseModel):
    job_description: str
    min_years_experience: Optional[float] = 0.0
    required_seniority: Optional[str] = None
    top_k: int = 10
    weight_cosine: float = 0.35
    weight_bert: float = 0.45
    weight_experience: float = 0.20

class ScoreBreakdown(BaseModel):
    cosine_similarity: float
    bert_rerank_score: float
    experience_depth_score: float
    composite_score: float

class SearchCandidateResult(BaseModel):
    candidate_id: str
    file_hash: str
    filename: str
    full_name: str
    email: Optional[str] = None
    location: Optional[str] = None
    total_years_experience: float
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    score_breakdown: ScoreBreakdown
    experience_highlights: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    work_experiences: List[WorkExperienceItem] = Field(default_factory=list)

class SearchResponse(BaseModel):
    query_time_ms: float
    cache_hit: bool
    total_matches: int
    results: List[SearchCandidateResult]
