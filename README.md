# HyperATS: High-Performance Local ATS Parser & Experience Matcher

> [!NOTE]
> **Learning & Educational Project Disclaimer**  
> This repository is strictly an educational and experimental project created for learning purposes. It explores local vector search with `pgvector`, two-stage semantic ranking (Cosine ANN + BERT Cross-Encoder), microservice orchestration with FastAPI & Next.js, and multi-tier Redis caching. It is not intended for commercial ATS compliance or production recruiting usage.

---

## Overview

HyperATS is an experimental, microservice-based Applicant Tracking System engineered to process, vectorize, and search resumes with sub-10ms query times.

Rather than relying on naive keyword frequency matching, HyperATS explores evaluating **actual work experience**: extracting role tenures, career progression trajectories, leadership scope, and quantified **STAR achievements** (Situation, Task, Action, Result).

---

## Architecture

```
                               ┌───────────────────────────┐
                               │     Client Browser UI     │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                      ┌───────────────────────────────────────────────┐
                      │    Next.js Gateway & Minimal UI (:3000)       │
                      │  - Overview & System Telemetry                │
                      │  - Single / Batch PDF Resume Dropzone         │
                      │  - Semantic JD Matcher & Experience Inspector │
                      │  - Edge Proxy & Gateway Cache (/api/...)      │
                      └───────┬───────────────────────────────┬───────┘
                              │                               │
                       REST / Upload                   REST / Search
                              │                               │
                              ▼                               ▼
       ┌─────────────────────────────────────┐ ┌─────────────────────────────────────┐
       │ Ingestion & LLM Parsing Service     │ │ Orchestrator & Ranking Service      │
       │ (FastAPI - Port 8001)               │ │ (FastAPI - Port 8002)               │
       │ - PyMuPDF Fast Stream Extractor     │ │ - FastEmbed BAAI/bge-small-en-v1.5  │
       │ - LLM Experience Decomposer         │ │ - Stage 1: pgvector Cosine ANN      │
       │ - STAR Quantified Metric Extractor  │ │ - Stage 2: BERT Cross-Encoder       │
       │ - Deterministic NLP Heuristic Engine│ │ - Experience Depth & Trajectory     │
       └──────────────────┬──────────────────┘ └──────────────────┬──────────────────┘
                          │                                       │
                          └───────────────────┬───────────────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
       ┌────────────────────────┐                          ┌────────────────────────┐
       │     PostgreSQL 16      │                          │        Redis 7         │
       │     with pgvector      │                          │   Multi-Tier Caching   │
       │ - candidates table     │                          │ - File Hash Dedup      │
       │ - work_experiences     │                          │ - Parsed JSON Cache    │
       │ - candidate_embeddings │                          │ - Embedding Vector C.  │
       │ - HNSW Cosine Index    │                          │ - Cross-Encoder Cache  │
       │   (m=16, ef_const=64)  │                          │ - Query Result Cache   │
       └────────────────────────┘                          └────────────────────────┘
```

---

## Key Concepts Explored

### 1. Work Experience Evaluation vs Naive Keywords
| Feature | Traditional Keyword Matching | HyperATS Experience Evaluation |
| :--- | :--- | :--- |
| **Detection Basis** | Raw keyword frequency (e.g. word count) | Extracted job tenure duration, seniority progression |
| **Spam Resistance** | Vulnerable to keyword stuffing | Penalizes keyword spam lacking verified tenure or impact |
| **Recency & Progression** | Treats 8-year-old mention same as recent role | Weights recent primary roles higher; rewards career progression |
| **Quantified Impact** | Ignored | Extracts STAR metrics (e.g., "85% latency reduction", "25M daily requests") |
| **Scoring Formulation** | Keyword count / Total keywords | `0.35 * Cosine_ANN + 0.45 * BERT_CrossEncoder + 0.20 * Experience_Depth` |

### 2. Multi-Level Redis Caching
- **File Deduplication Cache (`cache:file_hash:<sha256>`)**: Skips re-parsing identical PDFs (0ms).
- **Parsed Document Cache (`cache:parsed_text:<sha256>`)**: Caches structured JSON from raw text.
- **Dense Embedding Cache (`cache:embed:<sha256>`)**: Stores 384-dimensional packed vectors.
- **Cross-Encoder Score Cache (`cache:cross:<jd_hash>:<cand_hash>`)**: Caches BERT cross-attention pairs.
- **Search Query Cache (`cache:query:<sha256>`)**: Delivers repeated search queries in `< 2ms` with automated invalidation.

---

## Quickstart

### Option 1: Docker Compose (All Services)
```bash
# Start all microservices and database infrastructure
docker-compose up -d

# Check status
docker-compose ps
```

Services:
- **Next.js Web UI & Gateway**: `http://localhost:3000`
- **Ingestion Service API**: `http://localhost:8001/docs`
- **Orchestrator Service API**: `http://localhost:8002/docs`
- **PostgreSQL pgvector**: `localhost:5432` (`ats_parser_db`)
- **Redis Cache**: `localhost:6379`

### Option 2: Local Development
```bash
# 1. Start Postgres (pgvector) and Redis
docker-compose up -d postgres redis

# 2. Setup Python environment
uv venv .venv
source .venv/bin/activate
uv pip install -r services/ingestion-service/requirements.txt
uv pip install -r services/orchestrator-service/requirements.txt
uv pip install -r services/worker-service/requirements.txt

# 3. Start Ingestion Service (Port 8001)
PYTHONPATH=services/ingestion-service uvicorn app.main:app --port 8001 &

# 4. Start Orchestrator Service (Port 8002)
PYTHONPATH=services/orchestrator-service uvicorn app.main:app --port 8002 &

# 5. Start Next.js Frontend Gateway (Port 3000)
cd frontend-gateway
pnpm install
pnpm run dev
```

---

## Bulk Ingestion & Ranking Tool

For processing folders of hundreds or thousands of resumes:

```bash
# Ingest local folder of resumes and rank against a Job Description:
python scripts/bulk_ingest_and_rank.py \
  --folder /path/to/resumes \
  --jd "Senior Distributed Backend Engineer with 5+ years experience in Go/Python and Redis." \
  --min-years 3.0 \
  --top-k 15
```

---

## Running Test Suites

```bash
# Ingestion Service tests (PyMuPDF text extraction, STAR impact detection)
PYTHONPATH=services/ingestion-service pytest services/ingestion-service/tests/ -v

# Orchestrator tests (pgvector embeddings, BERT Cross-Encoder, experience vs keyword scoring)
PYTHONPATH=services/orchestrator-service pytest services/orchestrator-service/tests/ -v

# Batch Worker tests (concurrency gating, pub/sub streaming)
PYTHONPATH=services/worker-service pytest services/worker-service/tests/ -v
```

---

## License

This project is open-source under the MIT License for educational and learning purposes.
