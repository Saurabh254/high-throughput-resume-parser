#!/usr/bin/env python3
"""
CLI tool to bulk ingest a directory or ZIP of resumes and rank them against a Job Description.

Usage:
  python scripts/bulk_ingest_and_rank.py --folder /path/to/resumes --jd "Your Job Description"
  python scripts/bulk_ingest_and_rank.py --zip /path/to/resumes.zip --jd "Your Job Description"
"""

import argparse
import glob
import os
import sys
import time
import zipfile
import httpx

INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://127.0.0.1:8001")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://127.0.0.1:8002")


def ingest_folder(folder_path: str):
    pdf_files = glob.glob(os.path.join(folder_path, "**/*.pdf"), recursive=True)
    if not pdf_files:
        print(f"❌ No PDF files found in {folder_path}")
        return

    print(f"📁 Found {len(pdf_files)} PDF resumes. Starting ingestion...")
    start_time = time.time()
    success = 0
    cached = 0
    failed = 0

    with httpx.Client(timeout=60.0) as client:
        for idx, pdf_path in enumerate(pdf_files, 1):
            fname = os.path.basename(pdf_path)
            try:
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                files = {"file": (fname, pdf_bytes, "application/pdf")}
                data = {"auto_index": "true"}
                res = client.post(f"{INGESTION_URL}/api/v1/parse/pdf", files=files, data=data)

                if res.status_code == 200:
                    resp_json = res.json()
                    if resp_json.get("cached"):
                        cached += 1
                    else:
                        success += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1

            if idx % 25 == 0 or idx == len(pdf_files):
                print(f"  Processed {idx}/{len(pdf_files)} resumes... (Success: {success}, Cached: {cached}, Failed: {failed})")

    elapsed = time.time() - start_time
    rate = len(pdf_files) / max(0.001, elapsed)
    print(f"✅ Ingestion complete in {elapsed:.2f}s ({rate:.1f} resumes/sec)\n")


def rank_resumes(job_description: str, min_years: float = 3.0, top_k: int = 15):
    print(f"🔍 Ranking candidates against Job Description...")
    start_time = time.time()

    payload = {
        "job_description": job_description,
        "min_years_experience": min_years,
        "top_k": top_k,
        "weight_cosine": 0.35,
        "weight_bert": 0.45,
        "weight_experience": 0.20,
    }

    with httpx.Client(timeout=30.0) as client:
        res = client.post(f"{ORCHESTRATOR_URL}/api/v1/search", json=payload)
        if res.status_code != 200:
            print(f"❌ Search failed: {res.text}")
            return

        data = res.json()

    elapsed_ms = data.get("query_time_ms", (time.time() - start_time) * 1000)
    results = data.get("results", [])

    print(f"\n📊 Match Results ({len(results)} shown of {data.get('total_matches')} total, query took {elapsed_ms:.1f}ms):")
    print("=" * 80)

    for idx, c in enumerate(results, 1):
        score = c["score_breakdown"]
        comp_pct = score["composite_score"] * 100
        cos_pct = score["cosine_similarity"] * 100
        bert_pct = score["bert_rerank_score"] * 100
        exp_pct = score["experience_depth_score"] * 100

        print(f"#{idx:02d} {c['full_name']} — {comp_pct:.1f}% Match ({c['total_years_experience']} yrs exp)")
        print(f"     Role: {c['current_role']} at {c['current_company']}")
        print(f"     Score Breakdown: [pgvector Cosine: {cos_pct:.1f}% | BERT Rerank: {bert_pct:.1f}% | Experience Depth: {exp_pct:.1f}%]")
        if c.get("experience_highlights"):
            print(f"     Highlights: {' • '.join(c['experience_highlights'][:2])}")
        print("-" * 80)


def main():
    parser = argparse.ArgumentParser(description="Bulk Ingest and Rank Resumes")
    parser.add_argument("--folder", type=str, help="Path to folder containing PDF resumes")
    parser.add_argument("--jd", type=str, required=True, help="Job Description text or path to JD text file")
    parser.add_argument("--min-years", type=float, default=0.0, help="Minimum required years of experience")
    parser.add_argument("--top-k", type=int, default=10, help="Number of top candidates to display")

    args = parser.parse_args()

    # Load JD text from file if path provided
    jd_text = args.jd
    if os.path.isfile(args.jd):
        with open(args.jd, "r", encoding="utf-8") as f:
            jd_text = f.read()

    # Ingest folder if provided
    if args.folder:
        ingest_folder(args.folder)

    # Rank
    rank_resumes(job_description=jd_text, min_years=args.min_years, top_k=args.top_k)


if __name__ == "__main__":
    main()
