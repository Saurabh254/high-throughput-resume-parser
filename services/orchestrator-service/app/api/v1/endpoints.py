import hashlib
import json
import logging
import os
import numpy as np

# Import common models
import sys
import time
from typing import Any

from app.cache.redis_cache import cache
from app.core.config import settings
from app.core.database import db
from app.core.embedder import embedder
from app.core.experience_evaluator import ExperienceEvaluator
from app.core.reranker import reranker
from fastapi import APIRouter, HTTPException

try:
    from app.models.common import (
        CandidateProfile,
        ScoreBreakdown,
        SearchCandidateResult,
        SearchRequest,
        SearchResponse,
    )
except ImportError:
    sys.path.append(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../shared"))
    )
    from models.common import (
        CandidateProfile,
        ScoreBreakdown,
        SearchCandidateResult,
        SearchRequest,
        SearchResponse,
    )

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/index/candidate", response_model=dict[str, Any])
async def index_candidate(profile: CandidateProfile):
    """
    Indexes candidate profile:
    1. Computes dense vectors for overall profile, experience narrative, and skills.
    2. Stores in PostgreSQL (candidates, work_experiences, candidate_embeddings).
    3. Invalidates search query cache.
    """
    pool = await db.get_pool()
    if not pool:
        raise HTTPException(status_code=503, detail="PostgreSQL database unavailable")

    try:
        # Compute embeddings (FastEmbed / ONNX + Redis cache)
        overall_text = f"{profile.metadata.full_name}. {profile.experience_summary}. Skills: {', '.join(profile.core_skills)}"
        experience_text = profile.experience_summary or overall_text
        skills_text = ", ".join(profile.core_skills) or overall_text

        overall_vec = await embedder.embed_text(overall_text)
        exp_vec = await embedder.embed_text(experience_text)
        skills_vec = await embedder.embed_text(skills_text)

        async with pool.acquire() as conn:
            async with conn.transaction():
                # Upsert into candidates table
                candidate_row = await conn.fetchrow(
                    """
                    INSERT INTO candidates (
                        file_hash, filename, full_name, email, phone,
                        location, linkedin_url, github_url, total_years_experience,
                        raw_text, parsed_json, updated_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (file_hash) DO UPDATE SET
                        filename = EXCLUDED.filename,
                        full_name = EXCLUDED.full_name,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone,
                        location = EXCLUDED.location,
                        linkedin_url = EXCLUDED.linkedin_url,
                        github_url = EXCLUDED.github_url,
                        total_years_experience = EXCLUDED.total_years_experience,
                        raw_text = EXCLUDED.raw_text,
                        parsed_json = EXCLUDED.parsed_json,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id;
                    """,
                    profile.file_hash,
                    profile.filename,
                    profile.metadata.full_name,
                    profile.metadata.email,
                    profile.metadata.phone,
                    profile.metadata.location,
                    profile.metadata.linkedin_url,
                    profile.metadata.github_url,
                    profile.total_years_experience,
                    profile.raw_text,
                    json.dumps(profile.model_dump()),
                )
                candidate_id = candidate_row["id"]

                # Clean existing experiences for this candidate
                await conn.execute(
                    "DELETE FROM work_experiences WHERE candidate_id = $1;",
                    candidate_id,
                )

                # Insert work experiences
                for exp in profile.work_experiences:
                    await conn.execute(
                        """
                        INSERT INTO work_experiences (
                            candidate_id, company, job_title, standardized_role,
                            seniority_level, start_date, end_date, duration_months,
                            is_current, technologies_used, impact_metrics,
                            experience_narrative, order_index
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12, $13
                        );
                        """,
                        candidate_id,
                        exp.company,
                        exp.job_title,
                        exp.standardized_role,
                        exp.seniority_level,
                        exp.start_date,
                        exp.end_date,
                        exp.duration_months,
                        exp.is_current,
                        exp.technologies_used,
                        json.dumps(exp.impact_metrics),
                        exp.experience_narrative,
                        exp.order_index,
                    )

                # Upsert into candidate_embeddings table using pgvector registered types
                vec_overall = np.array(overall_vec, dtype=np.float32)
                vec_exp = np.array(exp_vec, dtype=np.float32)
                vec_skills = np.array(skills_vec, dtype=np.float32)

                await conn.execute(
                    """
                    INSERT INTO candidate_embeddings (
                        candidate_id, overall_vector, experience_vector, skills_vector
                    ) VALUES (
                        $1, $2, $3, $4
                    )
                    ON CONFLICT (candidate_id) DO UPDATE SET
                        overall_vector = EXCLUDED.overall_vector,
                        experience_vector = EXCLUDED.experience_vector,
                        skills_vector = EXCLUDED.skills_vector;
                    """,
                    candidate_id, vec_overall, vec_exp, vec_skills
                )

        # Invalidate search query cache on new index update
        await cache.invalidate_query_cache()

        return {
            "status": "indexed",
            "candidate_id": str(candidate_id),
            "file_hash": profile.file_hash,
            "full_name": profile.metadata.full_name,
        }

    except Exception as e:
        logger.exception(f"Error indexing candidate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to index candidate: {e!s}")


@router.post("/search", response_model=SearchResponse)
async def search_candidates(request: SearchRequest):
    """
    Two-Stage Search Pipeline:
    Stage 1: pgvector Cosine ANN Search (retrieves top coarse candidates in < 10ms).
    Stage 2: BERT Cross-Encoder Re-ranking + Experience Depth & Trajectory Evaluation.
    """
    start_time = time.time()

    # 0. Check Search Query Cache
    query_str = f"{request.job_description}_{request.min_years_experience}_{request.required_seniority}_{request.top_k}_{request.weight_cosine}_{request.weight_bert}_{request.weight_experience}"
    query_hash = hashlib.sha256(query_str.encode("utf-8")).hexdigest()

    cached_res = await cache.get_query_cache(query_hash)
    if cached_res:
        cached_res["query_time_ms"] = round((time.time() - start_time) * 1000, 2)
        cached_res["cache_hit"] = True
        return SearchResponse(**cached_res)

    pool = await db.get_pool()
    if not pool:
        raise HTTPException(status_code=503, detail="PostgreSQL database unavailable")

    try:
        # Step 1: Embed Job Description
        query_vec = await embedder.embed_text(request.job_description)
        vec_query = np.array(query_vec, dtype=np.float32)

        # Step 2: Stage 1 Cosine ANN Search on pgvector
        # 1 - (ce.experience_vector <=> query_vec) gives cosine similarity in [-1, 1]
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    c.id, c.file_hash, c.filename, c.full_name, c.email, c.location,
                    c.total_years_experience, c.parsed_json,
                    (1 - (ce.experience_vector <=> $1)) AS cosine_sim
                FROM candidate_embeddings ce
                JOIN candidates c ON c.id = ce.candidate_id
                ORDER BY ce.experience_vector <=> $1 ASC
                LIMIT $2;
                """,
                vec_query,
                settings.DEFAULT_COARSE_TOP_K,
            )

        if not rows:
            return SearchResponse(
                query_time_ms=round((time.time() - start_time) * 1000, 2),
                cache_hit=False,
                total_matches=0,
                results=[],
            )

        # Step 3 & 4: Stage 2 BERT Reranking & Experience Depth Scoring
        candidates_scored: list[SearchCandidateResult] = []

        for row in rows:
            cand_id = str(row["id"])
            raw_parsed = row["parsed_json"]
            profile_data = (
                json.loads(raw_parsed) if isinstance(raw_parsed, str) else raw_parsed
            )
            profile = CandidateProfile(**profile_data)

            # Cosine similarity normalized to [0, 1]
            cosine_sim = max(0.0, min(1.0, float(row["cosine_sim"] or 0.0)))

            # Stage 2: BERT Cross-Encoder Score on Candidate Experience Narrative
            exp_narrative = profile.experience_summary or profile.raw_text[:800]
            bert_score = await reranker.compute_score(
                request.job_description, exp_narrative
            )

            # Stage 2: Actual Work Experience Depth Evaluation
            depth_score, highlights = ExperienceEvaluator.evaluate_candidate_experience(
                profile=profile,
                min_years_required=request.min_years_experience or 0.0,
                required_seniority=request.required_seniority,
            )

            # Composite Formula:
            # Final = (w_cos * Cosine_Sim) + (w_bert * BERT_Score) + (w_exp * Depth_Score)
            w_cos = request.weight_cosine
            w_bert = request.weight_bert
            w_exp = request.weight_experience
            total_weight = w_cos + w_bert + w_exp or 1.0

            composite_score = (
                (w_cos * cosine_sim) + (w_bert * bert_score) + (w_exp * depth_score)
            ) / total_weight

            # Matched skills
            matched_skills = [
                s
                for s in profile.core_skills
                if s.lower() in request.job_description.lower()
            ]

            first_exp = (
                profile.work_experiences[0] if profile.work_experiences else None
            )

            candidates_scored.append(
                SearchCandidateResult(
                    candidate_id=cand_id,
                    file_hash=row["file_hash"],
                    filename=row["filename"],
                    full_name=row["full_name"]
                    or profile.metadata.full_name
                    or "Anonymous",
                    email=row["email"] or profile.metadata.email,
                    location=row["location"] or profile.metadata.location,
                    total_years_experience=float(row["total_years_experience"] or 0.0),
                    current_role=first_exp.job_title if first_exp else "Professional",
                    current_company=first_exp.company if first_exp else "Industry",
                    score_breakdown=ScoreBreakdown(
                        cosine_similarity=round(cosine_sim, 4),
                        bert_rerank_score=round(bert_score, 4),
                        experience_depth_score=round(depth_score, 4),
                        composite_score=round(composite_score, 4),
                    ),
                    experience_highlights=highlights,
                    matched_skills=matched_skills,
                    work_experiences=profile.work_experiences,
                )
            )

        # Sort by composite score descending
        candidates_scored.sort(
            key=lambda c: c.score_breakdown.composite_score, reverse=True
        )
        top_candidates = candidates_scored[: request.top_k]

        total_time_ms = round((time.time() - start_time) * 1000, 2)
        response = SearchResponse(
            query_time_ms=total_time_ms,
            cache_hit=False,
            total_matches=len(candidates_scored),
            results=top_candidates,
        )

        # Cache response in Redis
        await cache.set_query_cache(
            query_hash, response.model_dump(), ttl=settings.QUERY_CACHE_TTL
        )
        return response

    except Exception as e:
        logger.error(f"Search execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}")


@router.get("/candidates/{candidate_id}", response_model=dict[str, Any])
async def get_candidate(candidate_id: str):
    """Retrieves full candidate record and parsed JSON."""
    pool = await db.get_pool()
    if not pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, file_hash, filename, full_name, email, phone, location,
                   linkedin_url, github_url, total_years_experience, raw_text,
                   parsed_json, created_at, updated_at
            FROM candidates WHERE id = $1::uuid;
            """,
            candidate_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Candidate not found")

        experiences = await conn.fetch(
            """
            SELECT id, company, job_title, standardized_role, seniority_level,
                   start_date, end_date, duration_months, is_current,
                   technologies_used, impact_metrics, experience_narrative, order_index
            FROM work_experiences WHERE candidate_id = $1::uuid
            ORDER BY order_index ASC;
            """,
            candidate_id,
        )

    parsed_json = row["parsed_json"]
    profile_data = (
        json.loads(parsed_json) if isinstance(parsed_json, str) else parsed_json
    )

    return {
        "candidate": dict(row),
        "experiences": [dict(e) for e in experiences],
        "profile": profile_data,
    }


@router.get("/stats", response_model=dict[str, Any])
async def get_system_stats():
    """Returns database size, candidate counts, and index statistics."""
    pool = await db.get_pool()
    if not pool:
        return {"status": "degraded", "database": "offline"}

    async with pool.acquire() as conn:
        cand_count = await conn.fetchval("SELECT count(*) FROM candidates;")
        exp_count = await conn.fetchval("SELECT count(*) FROM work_experiences;")
        embed_count = await conn.fetchval("SELECT count(*) FROM candidate_embeddings;")

    return {
        "status": "operational",
        "total_candidates": cand_count,
        "total_work_experiences": exp_count,
        "total_embeddings": embed_count,
        "embedding_dimensions": settings.EMBEDDING_DIM,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "reranker_model": settings.RERANKER_MODEL_NAME,
    }


@router.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: str):
    """Deletes candidate from database and cleans caches."""
    pool = await db.get_pool()
    if not pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    async with pool.acquire() as conn:
        res = await conn.execute(
            "DELETE FROM candidates WHERE id = $1::uuid;", candidate_id
        )
        if res == "DELETE 0":
            raise HTTPException(status_code=404, detail="Candidate not found")

    await cache.invalidate_query_cache()
    return {"status": "deleted", "candidate_id": candidate_id}
