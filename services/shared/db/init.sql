-- High-Performance ATS Parser Schema with pgvector
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Candidates master table
CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(64),
    location VARCHAR(255),
    linkedin_url TEXT,
    github_url TEXT,
    total_years_experience NUMERIC(4, 1) DEFAULT 0,
    raw_text TEXT NOT NULL,
    parsed_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Granular Work Experience Decomposition Table
CREATE TABLE IF NOT EXISTS work_experiences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    company VARCHAR(255) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    standardized_role VARCHAR(128),
    seniority_level VARCHAR(64),
    start_date VARCHAR(64),
    end_date VARCHAR(64),
    duration_months INT DEFAULT 0,
    is_current BOOLEAN DEFAULT FALSE,
    technologies_used TEXT[] DEFAULT '{}',
    impact_metrics JSONB DEFAULT '[]'::jsonb,
    experience_narrative TEXT NOT NULL,
    order_index INT DEFAULT 0
);

-- Candidate Vector Embeddings Table
-- Dimension 384 corresponds to BAAI/bge-small-en-v1.5 and sentence-transformers/all-MiniLM-L6-v2
CREATE TABLE IF NOT EXISTS candidate_embeddings (
    candidate_id UUID PRIMARY KEY REFERENCES candidates(id) ON DELETE CASCADE,
    overall_vector vector(384) NOT NULL,
    experience_vector vector(384) NOT NULL,
    skills_vector vector(384) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_candidates_file_hash ON candidates(file_hash);
CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);
CREATE INDEX IF NOT EXISTS idx_work_exp_candidate_id ON work_experiences(candidate_id);
CREATE INDEX IF NOT EXISTS idx_work_exp_role ON work_experiences(standardized_role);
CREATE INDEX IF NOT EXISTS idx_work_exp_seniority ON work_experiences(seniority_level);

-- HNSW Vector Cosine Indexes for Sub-10ms ANN Search Across Millions of Candidates
CREATE INDEX IF NOT EXISTS idx_candidate_embeddings_overall_hnsw 
    ON candidate_embeddings USING hnsw (overall_vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_candidate_embeddings_experience_hnsw 
    ON candidate_embeddings USING hnsw (experience_vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
