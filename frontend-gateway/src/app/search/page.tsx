"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Search,
  ArrowRight,
  Clock,
  Loader2,
  Check,
  Briefcase,
  User,
} from "lucide-react";
import { SearchResponse } from "@/types";

const JD_TEMPLATES = [
  {
    title: "Senior Distributed Backend",
    text: "We are seeking a Senior Distributed Systems Engineer with 5+ years of experience designing high-throughput backend pipelines. Must have hands-on experience with Go or Python, Redis caching, event-driven microservices, and database query optimization. Strong preference for candidates who have led engineering initiatives, improved API latency, and maintained 99.99%+ uptime SLAs."
  },
  {
    title: "Staff Platform & SRE",
    text: "Looking for a Staff Platform / SRE Engineer with 7+ years of experience managing large-scale distributed cloud infrastructure, Kubernetes clusters, and automated chaos testing. Must have demonstrated history of cloud cost reduction, latency optimization, and mentoring engineering teams."
  },
  {
    title: "Junior Web Developer",
    text: "Entry-level or Junior Web Developer with 1+ years of experience in JavaScript, React, and web technologies. Looking for an enthusiastic learner eager to contribute to frontend and backend codebases."
  }
];

export default function SearchPage() {
  const [jdText, setJdText] = useState(JD_TEMPLATES[0].text);
  const [minYears, setMinYears] = useState(5.0);
  const [seniority, setSeniority] = useState("Senior");
  const [weightCosine, setWeightCosine] = useState(0.35);
  const [weightBert, setWeightBert] = useState(0.45);
  const [weightExp, setWeightExp] = useState(0.20);
  const [searching, setSearching] = useState(false);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (overrideJd?: string) => {
    const textToSearch = overrideJd ?? jdText;
    if (!textToSearch.trim()) return;

    setSearching(true);
    setError(null);

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: textToSearch,
          min_years_experience: minYears,
          required_seniority: seniority === "All" ? null : seniority,
          top_k: 10,
          weight_cosine: weightCosine,
          weight_bert: weightBert,
          weight_experience: weightExp,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setResponse(data);
      } else {
        const err = await res.json();
        setError(err.error || "Search request failed");
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-4">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Semantic Search &amp; Ranking</h1>
        <p className="text-zinc-400 text-xs mt-1">
          Two-stage candidate matching: pgvector Cosine ANN search coarse filter combined with BERT Cross-Encoder and Experience Trajectory ranking.
        </p>
      </div>

      {/* Preset JD templates */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] text-zinc-500 font-mono mr-1">Templates:</span>
        {JD_TEMPLATES.map((tmpl, idx) => (
          <button
            key={idx}
            onClick={() => {
              setJdText(tmpl.text);
              handleSearch(tmpl.text);
            }}
            className="text-xs px-2.5 py-1 rounded-md border border-border bg-surface hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            {tmpl.title}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Input and Filters */}
        <div className="lg:col-span-1 space-y-4">
          <div className="p-4 rounded-xl border border-border bg-surface space-y-4">
            <div className="text-[11px] font-mono uppercase text-zinc-500">Job Description</div>
            <textarea
              rows={8}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste Job Description here..."
              className="w-full text-xs text-zinc-200 bg-zinc-950 border border-border rounded-lg p-3 focus:outline-none focus:border-zinc-600 transition-colors leading-relaxed"
            />

            <div className="space-y-3 pt-2 border-t border-border">
              <div>
                <div className="flex justify-between text-xs text-zinc-300 mb-1">
                  <span>Min Experience</span>
                  <span className="font-mono text-zinc-100">{minYears} yrs</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="10"
                  step="0.5"
                  value={minYears}
                  onChange={(e) => setMinYears(parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-300 mb-1">
                  Required Seniority
                </label>
                <select
                  value={seniority}
                  onChange={(e) => setSeniority(e.target.value)}
                  className="w-full text-xs text-zinc-200 bg-zinc-950 border border-border rounded-lg p-2 focus:outline-none focus:border-zinc-600"
                >
                  <option value="All">All Levels</option>
                  <option value="Junior">Junior</option>
                  <option value="Mid">Mid-Level</option>
                  <option value="Senior">Senior</option>
                  <option value="Lead">Lead / Staff</option>
                  <option value="Principal">Principal</option>
                </select>
              </div>

              {/* Weights */}
              <div className="space-y-2 pt-2 border-t border-border">
                <div className="text-[11px] font-mono uppercase text-zinc-500">Scoring Weights</div>

                <div className="space-y-2 text-[11px] text-zinc-400">
                  <div className="flex justify-between">
                    <span>Cosine Vector (Stage 1):</span>
                    <span className="font-mono text-zinc-200">{(weightCosine * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="0.8"
                    step="0.05"
                    value={weightCosine}
                    onChange={(e) => setWeightCosine(parseFloat(e.target.value))}
                    className="w-full"
                  />

                  <div className="flex justify-between">
                    <span>BERT Cross-Encoder (Stage 2):</span>
                    <span className="font-mono text-zinc-200">{(weightBert * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="0.8"
                    step="0.05"
                    value={weightBert}
                    onChange={(e) => setWeightBert(parseFloat(e.target.value))}
                    className="w-full"
                  />

                  <div className="flex justify-between">
                    <span>Experience Depth (STAR):</span>
                    <span className="font-mono text-zinc-200">{(weightExp * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="0.8"
                    step="0.05"
                    value={weightExp}
                    onChange={(e) => setWeightExp(parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>
            </div>

            <button
              onClick={() => handleSearch()}
              disabled={searching || !jdText.trim()}
              className="w-full py-2 rounded-lg bg-zinc-100 hover:bg-zinc-200 text-zinc-950 font-medium text-xs flex items-center justify-center space-x-1.5 transition-colors disabled:opacity-50"
            >
              {searching ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Search className="w-3.5 h-3.5" />
              )}
              <span>Execute Search</span>
            </button>
          </div>
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-2 space-y-3">
          {response && (
            <div className="flex items-center justify-between text-xs text-zinc-500 bg-surface px-3 py-2 rounded-lg border border-border font-mono text-[11px]">
              <div className="flex items-center space-x-3">
                <span className="text-zinc-300 font-medium">
                  {response.total_matches} candidate{response.total_matches === 1 ? "" : "s"}
                </span>
                <span className="flex items-center text-zinc-500">
                  <Clock className="w-3 h-3 mr-1" />
                  {response.query_time_ms} ms
                </span>
              </div>
              <div>
                {response.cache_hit ? (
                  <span className="text-zinc-400">Redis Cache Hit</span>
                ) : (
                  <span className="text-zinc-500">Live 2-Stage Compute</span>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-rose-400 text-xs">
              {error}
            </div>
          )}

          {!response && !searching && (
            <div className="p-12 text-center rounded-xl border border-border bg-surface/30 space-y-2">
              <Search className="w-6 h-6 text-zinc-600 mx-auto" />
              <div className="text-xs font-medium text-zinc-300">No Search Executed</div>
              <p className="text-[11px] text-zinc-500 max-w-xs mx-auto">
                Paste a Job Description on the left and click Execute Search.
              </p>
            </div>
          )}

          {response && response.results.length === 0 && (
            <div className="p-12 text-center rounded-xl border border-border bg-surface/30 space-y-2">
              <User className="w-6 h-6 text-zinc-600 mx-auto" />
              <div className="text-xs font-medium text-zinc-300">No Matching Candidates</div>
              <p className="text-[11px] text-zinc-500 max-w-xs mx-auto">
                No candidates in the database matched these criteria.
              </p>
            </div>
          )}

          {response?.results.map((cand, idx) => {
            const compositePct = Math.round(cand.score_breakdown.composite_score * 100);
            const cosinePct = Math.round(cand.score_breakdown.cosine_similarity * 100);
            const bertPct = Math.round(cand.score_breakdown.bert_rerank_score * 100);
            const depthPct = Math.round(cand.score_breakdown.experience_depth_score * 100);

            return (
              <div
                key={cand.candidate_id}
                className="p-4 sm:p-5 rounded-xl border border-border bg-surface hover:border-zinc-700 transition-colors space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-[11px] text-zinc-500 font-mono">
                        #{idx + 1}
                      </span>
                      <h3 className="text-sm font-semibold text-zinc-100">{cand.full_name}</h3>
                      <span className="text-[11px] text-zinc-500">
                        • {cand.total_years_experience} yrs exp
                      </span>
                    </div>
                    <div className="text-xs text-zinc-400 mt-0.5 flex items-center space-x-1.5">
                      <Briefcase className="w-3 h-3 text-zinc-500" />
                      <span>{cand.current_role} at {cand.current_company}</span>
                      {cand.location && <span className="text-zinc-600">• {cand.location}</span>}
                    </div>
                  </div>

                  <div className="self-start sm:self-auto">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-md border border-border bg-zinc-900 text-zinc-200 font-mono text-xs font-medium">
                      {compositePct}% match
                    </span>
                  </div>
                </div>

                {/* Score Breakdown: Minimal Line */}
                <div className="flex items-center space-x-4 text-[11px] font-mono text-zinc-400 bg-zinc-950 px-3 py-2 rounded-lg border border-border">
                  <span>Cosine: <strong className="text-zinc-200">{cosinePct}%</strong></span>
                  <span className="text-zinc-700">•</span>
                  <span>BERT: <strong className="text-zinc-200">{bertPct}%</strong></span>
                  <span className="text-zinc-700">•</span>
                  <span>Experience Depth: <strong className="text-zinc-200">{depthPct}%</strong></span>
                </div>

                {/* Experience highlights */}
                {cand.experience_highlights.length > 0 && (
                  <ul className="space-y-1 text-xs text-zinc-400 pt-1">
                    {cand.experience_highlights.map((h, i) => (
                      <li key={i} className="flex items-start">
                        <Check className="w-3.5 h-3.5 text-zinc-400 mr-2 mt-0.5 shrink-0" />
                        <span>{h}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {/* Matched skills chips */}
                {cand.matched_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {cand.matched_skills.map((skill, sIdx) => (
                      <span
                        key={sIdx}
                        className="text-[10px] px-2 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-border"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                )}

                <div className="pt-2 flex justify-end border-t border-border/70">
                  <Link
                    href={`/candidates/${cand.candidate_id}`}
                    className="inline-flex items-center space-x-1 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
                  >
                    <span>View Career Timeline</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
