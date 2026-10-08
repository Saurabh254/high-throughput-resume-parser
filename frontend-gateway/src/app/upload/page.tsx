"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  UploadCloud,
  FileText,
  ArrowRight,
  Loader2,
  Check,
  AlertCircle,
} from "lucide-react";
import { CandidateProfile } from "@/types";

const BENCHMARK_CANDIDATES = [
  {
    filename: "alice_chen_senior_distributed.pdf",
    text: `Alice Chen
alice.chen@example.com | (415) 890-1234 | San Francisco, CA
linkedin.com/in/alicechen | github.com/alicechen

PROFESSIONAL EXPERIENCE

Senior Distributed Systems Engineer
Stripe | Jan 2021 - Present
• Architected core payment orchestration pipeline processing over 25M transactions daily with zero dropped events.
• Reduced p99 end-to-end API latency from 280ms to 42ms (85% reduction) by implementing Redis tiered caching and async connection pools.
• Designed distributed consensus and idempotent retry logic maintaining 99.999% uptime across multi-region deployments.
• Mentored 6 backend engineers and drove technical architecture design reviews.

Software Engineer
Airbnb | Jun 2018 - Dec 2020
• Developed distributed inventory search microservices utilizing Go, Python, and PostgreSQL.
• Increased search query throughput by 45% through database query optimization and covering indexes.
• Built Kafka real-time ingestion pipelines processing 50k events per second.

EDUCATION
University of California, Berkeley
B.S. in Computer Science | 2018

TECHNICAL SKILLS
Go, Python, PostgreSQL, Redis, Kafka, Kubernetes, AWS, Distributed Systems, Microservices, Event-Driven Architecture`
  },
  {
    filename: "bob_smith_keyword_spammer.pdf",
    text: `Bob Smith
bob.smith@example.com | (212) 555-9876 | New York, NY
linkedin.com/in/bobsmith | github.com/bobsmith

SUMMARY
Software Engineer with skills in Python, Go, Rust, Java, C++, React, Next.js, Vue, Angular, Node.js, Express, FastAPI, Django, PostgreSQL, MySQL, Redis, MongoDB, Cassandra, DynamoDB, Kafka, RabbitMQ, Docker, Kubernetes, AWS, GCP, Azure, Terraform, Distributed Systems, Microservices, Machine Learning, Deep Learning, AI, LLM, PyTorch, TensorFlow.

PROFESSIONAL EXPERIENCE

Junior Web Developer
Freelance | Jan 2023 - Present
• Worked on web applications using Python, Go, Rust, Java, C++, React, Next.js, Vue, Angular, Node.js, Express, FastAPI, Django.
• Handled database management with PostgreSQL, MySQL, Redis, MongoDB, Cassandra, DynamoDB.
• Deployed containers using Docker, Kubernetes, AWS, GCP, Azure, Terraform.
• Researched microservices and distributed systems.

EDUCATION
State College
Bachelor of Arts in General Studies | 2022

SKILLS
Python, Go, Rust, Java, C++, React, Next.js, PostgreSQL, Redis, Docker, Kubernetes, AWS`
  },
  {
    filename: "elena_rostova_staff_platform.pdf",
    text: `Elena Rostova
elena.rostova@example.com | (206) 555-4321 | Seattle, WA
linkedin.com/in/elenarostova | github.com/elenarostova

PROFESSIONAL EXPERIENCE

Staff Platform & Infrastructure Engineer
Cloudflare | Mar 2020 - Present
• Principal architect for global edge infrastructure orchestrating 3,500+ bare-metal nodes and Kubernetes clusters.
• Decreased multi-region infrastructure costs by $1.8M annually (38% cloud cost reduction) via automated resource rightsizing and autoscaling.
• Championed company-wide zero-downtime deployment platform achieving 99.999% SLA across all client-facing gateways.
• Led cross-functional team of 14 platform and SRE engineers across 4 timezones.

Senior Site Reliability Engineer
Uber | Aug 2016 - Feb 2020
• Spearheaded automated chaos testing and incident mitigation tooling for real-time dispatch systems.
• Reduced mean time to recovery (MTTR) by 62% during high-traffic surges.
• Built high-throughput telemetry pipelines digesting 5M metrics per second into distributed time-series databases.

EDUCATION
University of Washington
M.S. in Computer Science | 2016

TECHNICAL SKILLS
Kubernetes, Go, Python, Linux Internals, AWS, GCP, Terraform, Envoy, Redis, PostgreSQL, Distributed Observability`
  }
];

export default function UploadPage() {
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState<any[]>([]);
  const [dragActive, setDragActive] = useState(false);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);

    const newResults: any[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append("file", file);
      formData.append("auto_index", "true");

      try {
        const res = await fetch("/api/resumes/upload", {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          const data = await res.json();
          newResults.push({
            filename: file.name,
            cached: data.cached,
            profile: data.profile,
            hash: data.file_hash,
          });
        } else {
          const errData = await res.json();
          newResults.push({
            filename: file.name,
            error: errData.error || "Failed to parse PDF",
          });
        }
      } catch (err: any) {
        newResults.push({
          filename: file.name,
          error: err.message,
        });
      }
    }

    setUploadResults((prev) => [...newResults, ...prev]);
    setUploading(false);
  };

  const handlePopulateBenchmarks = async () => {
    setUploading(true);
    const newResults: any[] = [];

    for (const item of BENCHMARK_CANDIDATES) {
      try {
        const res = await fetch("/api/resumes/text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: item.text,
            filename: item.filename,
            auto_index: true,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          newResults.push({
            filename: item.filename,
            cached: data.cached,
            profile: data.profile,
            hash: data.profile.file_hash,
          });
        }
      } catch (err: any) {
        console.error(err);
      }
    }

    setUploadResults((prev) => [...newResults, ...prev]);
    setUploading(false);
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Resume Ingestion</h1>
          <p className="text-zinc-400 text-xs mt-1">
            In-memory text extraction, experience decomposition, 384-D vectorization, and pgvector storage.
          </p>
        </div>

        <button
          onClick={handlePopulateBenchmarks}
          disabled={uploading}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-border bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-zinc-100 text-xs font-medium transition-colors disabled:opacity-50 self-start"
        >
          {uploading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          <span>Load Benchmark Resumes</span>
        </button>
      </div>

      {/* Drag & Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          handleFileUpload(e.dataTransfer.files);
        }}
        className={`border border-dashed rounded-2xl p-10 text-center transition-colors ${
          dragActive
            ? "border-zinc-400 bg-zinc-900/40"
            : "border-border hover:border-zinc-700 bg-surface/50"
        }`}
      >
        <div className="max-w-sm mx-auto space-y-3">
          <div className="w-10 h-10 rounded-lg bg-zinc-900 border border-border flex items-center justify-center mx-auto text-zinc-400">
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin text-zinc-300" />
            ) : (
              <UploadCloud className="w-4 h-4" />
            )}
          </div>
          <div>
            <div className="text-xs font-medium text-zinc-200">
              {uploading ? "Extracting & Vectorizing Resumes..." : "Drop PDF resumes or select files"}
            </div>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              Supports PDF and ZIP files. File hash deduplication active.
            </p>
          </div>
          <div>
            <label className="cursor-pointer inline-flex items-center px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-zinc-200 text-zinc-950 text-xs font-medium transition-colors">
              <span>Choose Files</span>
              <input
                type="file"
                multiple
                accept=".pdf,.zip"
                disabled={uploading}
                onChange={(e) => handleFileUpload(e.target.files)}
                className="hidden"
              />
            </label>
          </div>
        </div>
      </div>

      {/* Uploaded History / Results */}
      {uploadResults.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs font-mono text-zinc-400 uppercase tracking-wider">
            Ingestion Results ({uploadResults.length})
          </div>

          <div className="rounded-xl border border-border bg-surface divide-y divide-border overflow-hidden">
            {uploadResults.map((item, idx) => {
              const prof: CandidateProfile = item.profile;
              return (
                <div
                  key={idx}
                  className="p-3.5 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-start space-x-3">
                    <div className="p-2 rounded-md bg-zinc-900 border border-border text-zinc-400 mt-0.5">
                      <FileText className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-zinc-200">
                          {prof?.metadata?.full_name || item.filename}
                        </span>
                        {item.cached ? (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border bg-zinc-900 text-zinc-400">
                            Dedup Cache (0ms)
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border bg-zinc-900 text-zinc-300">
                            Indexed
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-zinc-500 mt-1 flex flex-wrap gap-x-3">
                        <span>{item.filename}</span>
                        {prof && (
                          <>
                            <span>• {prof.total_years_experience} yrs exp</span>
                            <span>• {prof.work_experiences?.length || 0} roles</span>
                            <span>
                              • {prof.work_experiences?.reduce((acc, w) => acc + (w.impact_metrics?.length || 0), 0) || 0} STAR metrics
                            </span>
                          </>
                        )}
                        {item.error && (
                          <span className="text-rose-400 flex items-center">
                            <AlertCircle className="w-3 h-3 mr-1" />
                            {item.error}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <Link
                    href="/search"
                    className="inline-flex items-center space-x-1 text-xs text-zinc-400 hover:text-zinc-200 transition-colors self-start sm:self-auto"
                  >
                    <span>Match with JDs</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
