"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  UploadCloud,
  Search,
  Check,
  X,
} from "lucide-react";
import { SystemStats } from "@/types";

export default function DashboardPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/stats")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.status !== "offline") {
          setStats(data);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-10 max-w-5xl mx-auto py-4">
      {/* Hero */}
      <div className="space-y-4">
        <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded-md bg-zinc-900 border border-border text-[11px] text-zinc-400 font-mono">
          <span>Actual Work Experience Engine</span>
          <span className="text-zinc-600">•</span>
          <span>pgvector Cosine + BERT Rerank</span>
        </div>

        <h1 className="text-3xl sm:text-4xl font-semibold text-zinc-100 tracking-tight">
          High-performance resume parsing &amp; experience ranking.
        </h1>

        <p className="text-zinc-400 text-sm max-w-2xl leading-relaxed">
          Standard ATS parsers match keyword frequencies. HyperATS decomposes verified job tenures, evaluates quantified STAR impact metrics, and performs two-stage ANN retrieval with BERT cross-encoder reranking.
        </p>

        <div className="flex items-center space-x-3 pt-2">
          <Link
            href="/search"
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-zinc-100 hover:bg-zinc-200 text-zinc-950 text-xs font-medium transition-colors"
          >
            <Search className="w-3.5 h-3.5" />
            <span>Search Resumes</span>
            <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
          </Link>

          <Link
            href="/upload"
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-zinc-100 border border-border text-xs font-medium transition-colors"
          >
            <UploadCloud className="w-3.5 h-3.5 text-zinc-400" />
            <span>Upload Resumes</span>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-xl border border-border bg-surface">
          <div className="text-[11px] font-mono text-zinc-500 uppercase">Indexed Resumes</div>
          <div className="text-2xl font-semibold text-zinc-100 mt-2 font-mono">
            {loading ? "..." : (stats?.total_candidates ?? 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">Deduplicated in Postgres</div>
        </div>

        <div className="p-4 rounded-xl border border-border bg-surface">
          <div className="text-[11px] font-mono text-zinc-500 uppercase">Decomposed Roles</div>
          <div className="text-2xl font-semibold text-zinc-100 mt-2 font-mono">
            {loading ? "..." : (stats?.total_work_experiences ?? 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">Verified work tenures</div>
        </div>

        <div className="p-4 rounded-xl border border-border bg-surface">
          <div className="text-[11px] font-mono text-zinc-500 uppercase">Vector Space</div>
          <div className="text-2xl font-semibold text-zinc-100 mt-2 font-mono">
            384-D
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">HNSW cosine index</div>
        </div>

        <div className="p-4 rounded-xl border border-border bg-surface">
          <div className="text-[11px] font-mono text-zinc-500 uppercase">Query Latency</div>
          <div className="text-2xl font-semibold text-zinc-100 mt-2 font-mono">
            &lt; 5 ms
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">Redis multi-tier cache</div>
        </div>
      </div>

      {/* Comparison: Minimal and Clean */}
      <div className="p-6 rounded-2xl border border-border bg-surface/60 space-y-5">
        <div>
          <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
            Work Experience Evaluation vs Keyword Matching
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            How our two-stage architecture separates genuine engineering tenure from keyword spam.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-border/80 bg-zinc-900/40 space-y-3">
            <div className="text-xs font-semibold text-zinc-300 flex items-center justify-between">
              <span>Traditional Keyword ATS</span>
              <span className="text-[10px] text-zinc-500 font-mono">BM25 / Keyword Density</span>
            </div>
            <ul className="space-y-2 text-xs text-zinc-400">
              <li className="flex items-start">
                <X className="w-3.5 h-3.5 text-zinc-500 mr-2 mt-0.5 shrink-0" />
                <span>Counts keyword repetitions (typing &quot;Go, Python, AWS&quot; 50 times yields 99%).</span>
              </li>
              <li className="flex items-start">
                <X className="w-3.5 h-3.5 text-zinc-500 mr-2 mt-0.5 shrink-0" />
                <span>Treats an internship from 8 years ago with the same weight as a recent Staff role.</span>
              </li>
              <li className="flex items-start">
                <X className="w-3.5 h-3.5 text-zinc-500 mr-2 mt-0.5 shrink-0" />
                <span>Ignores business metrics, tenure duration, and actual project impact.</span>
              </li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-border bg-zinc-900/80 space-y-3">
            <div className="text-xs font-semibold text-zinc-100 flex items-center justify-between">
              <span>HyperATS Experience Engine</span>
              <span className="text-[10px] text-zinc-400 font-mono">Two-Stage + STAR</span>
            </div>
            <ul className="space-y-2 text-xs text-zinc-300">
              <li className="flex items-start">
                <Check className="w-3.5 h-3.5 text-zinc-300 mr-2 mt-0.5 shrink-0" />
                <span>Decomposes verified job tenures, role seniorities, and upward career progression.</span>
              </li>
              <li className="flex items-start">
                <Check className="w-3.5 h-3.5 text-zinc-300 mr-2 mt-0.5 shrink-0" />
                <span>Extracts quantified STAR metrics (e.g. &quot;85% latency reduction&quot;, &quot;25M daily requests&quot;).</span>
              </li>
              <li className="flex items-start">
                <Check className="w-3.5 h-3.5 text-zinc-300 mr-2 mt-0.5 shrink-0" />
                <span>Combines pgvector Cosine ANN retrieval with BERT Cross-Encoder joint attention.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
