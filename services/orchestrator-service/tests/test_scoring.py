import pytest
import numpy as np

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../shared")))
from models.common import CandidateProfile, CandidateMetadata, WorkExperienceItem

from app.core.experience_evaluator import ExperienceEvaluator
from app.core.embedder import embedder
from app.core.reranker import reranker

def test_experience_depth_rewards_real_experience_over_keywords():
    # Candidate A: 6 years, Senior, Quantified Impact
    candidate_a = CandidateProfile(
        metadata=CandidateMetadata(full_name="Alice Senior"),
        total_years_experience=6.0,
        work_experiences=[
            WorkExperienceItem(
                company="Tech Corp",
                job_title="Senior Backend Engineer",
                seniority_level="Senior",
                duration_months=36,
                is_current=True,
                impact_metrics=[
                    {"metric_type": "percentage", "raw_statement": "Reduced latency by 45%"},
                    {"metric_type": "scale", "raw_statement": "Scaled to 10M daily events"}
                ],
                experience_narrative="Senior Backend Engineer leading architecture and scaling distributed pipelines.",
                technologies_used=["Python", "Go", "PostgreSQL", "Redis"]
            ),
            WorkExperienceItem(
                company="Startup Inc",
                job_title="Software Engineer",
                seniority_level="Mid",
                duration_months=36,
                is_current=False,
                impact_metrics=[
                    {"metric_type": "team_size", "raw_statement": "Mentored 3 junior devs"}
                ],
                experience_narrative="Fullstack engineer building web services.",
                technologies_used=["Python", "React"]
            )
        ]
    )

    # Candidate B: Keyword Spammer with only 1 year experience and no metrics
    candidate_b = CandidateProfile(
        metadata=CandidateMetadata(full_name="Bob Keyword"),
        total_years_experience=1.0,
        work_experiences=[
            WorkExperienceItem(
                company="Freelance",
                job_title="Junior Developer",
                seniority_level="Junior",
                duration_months=12,
                is_current=True,
                impact_metrics=[],
                experience_narrative="Worked on Python, Go, Rust, React, AWS, Docker, Kubernetes, PostgreSQL, Redis, Kafka, Machine Learning, AI.",
                technologies_used=["Python", "Go", "Rust", "React", "AWS", "Docker", "Kubernetes", "PostgreSQL", "Redis", "Kafka"]
            )
        ]
    )

    score_a, highlights_a = ExperienceEvaluator.evaluate_candidate_experience(
        candidate_a, min_years_required=5.0, required_seniority="Senior"
    )

    score_b, highlights_b = ExperienceEvaluator.evaluate_candidate_experience(
        candidate_b, min_years_required=5.0, required_seniority="Senior"
    )

    assert score_a > score_b, f"Expected Alice ({score_a}) to outperform Bob ({score_b})"
    assert score_a >= 0.85
    assert score_b <= 0.50
    assert any("exceeds" in h.lower() for h in highlights_a)
    assert any("below requested" in h.lower() for h in highlights_b)

@pytest.mark.asyncio
async def test_embedder_vector_properties():
    vec = await embedder.embed_text("Senior Distributed Systems Engineer with Go and Redis")
    assert len(vec) == 384
    norm = np.linalg.norm(vec)
    assert pytest.approx(norm, 0.05) == 1.0

@pytest.mark.asyncio
async def test_reranker_scoring():
    query = "Looking for Senior Distributed Systems Engineer"
    matching_doc = "Senior Software Engineer designing distributed event pipelines with high availability"
    unrelated_doc = "Graphic designer creating vector logos in Adobe Photoshop"

    score_match = await reranker.compute_score(query, matching_doc)
    score_unrelated = await reranker.compute_score(query, unrelated_doc)

    assert 0.0 <= score_match <= 1.0
    assert 0.0 <= score_unrelated <= 1.0
    assert score_match > score_unrelated
