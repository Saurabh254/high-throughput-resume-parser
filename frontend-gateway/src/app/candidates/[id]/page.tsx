"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Mail,
  MapPin,
  Calendar,
  FileText,
  Loader2,
  Linkedin,
  Github,
} from "lucide-react";
import { WorkExperienceItem } from "@/types";

export default function CandidateDetailPage() {
  const params = useParams();
  const candidateId = params?.id as string;

  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
    if (!candidateId) return;

    fetch(`/api/candidates/${candidateId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Candidate not found");
        return res.json();
      })
      .then((d) => setData(d))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [candidateId]);

  if (loading) {
    return (
      <div className="py-24 text-center space-y-2">
        <Loader2 className="w-5 h-5 animate-spin text-zinc-400 mx-auto" />
        <p className="text-xs text-zinc-500 font-mono">Loading candidate record...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="py-16 text-center space-y-3">
        <h2 className="text-base font-semibold text-zinc-200">Candidate Not Found</h2>
        <p className="text-xs text-zinc-500">{error || "Unable to retrieve record."}</p>
        <Link
          href="/search"
          className="inline-flex items-center space-x-1.5 text-xs text-zinc-400 hover:text-zinc-200"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Search</span>
        </Link>
      </div>
    );
  }

  const cand = data.candidate;
  const experiences: WorkExperienceItem[] = data.profile?.work_experiences || [];
  const education = data.profile?.education || [];
  const meta = data.profile?.metadata || {};

  return (
    <div className="space-y-6 max-w-4xl mx-auto py-4">
      <div>
        <Link
          href="/search"
          className="inline-flex items-center space-x-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Search</span>
        </Link>
      </div>

      {/* Header */}
      <div className="p-5 sm:p-6 rounded-xl border border-border bg-surface space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">
              {cand.full_name || meta.full_name || "Candidate Profile"}
            </h1>
            <div className="text-xs text-zinc-400 mt-1 flex items-center space-x-2">
              <span className="font-mono text-zinc-300">
                {cand.total_years_experience} yrs verified experience
              </span>
              <span className="text-zinc-600">•</span>
              <span className="text-zinc-500">{cand.filename}</span>
            </div>
          </div>

          <button
            onClick={() => setShowRaw(!showRaw)}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-border bg-zinc-900 hover:bg-zinc-800 text-zinc-300 text-xs font-medium transition-colors self-start"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>{showRaw ? "Hide Text" : "View Raw Resume"}</span>
          </button>
        </div>

        {/* Contact Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-zinc-400 font-mono">
          {(cand.email || meta.email) && (
            <span className="inline-flex items-center px-2 py-0.5 rounded border border-border bg-zinc-950">
              <Mail className="w-3 h-3 mr-1 text-zinc-500" />
              {cand.email || meta.email}
            </span>
          )}
          {(cand.location || meta.location) && (
            <span className="inline-flex items-center px-2 py-0.5 rounded border border-border bg-zinc-950">
              <MapPin className="w-3 h-3 mr-1 text-zinc-500" />
              {cand.location || meta.location}
            </span>
          )}
          {meta.linkedin_url && (
            <a
              href={meta.linkedin_url.startsWith("http") ? meta.linkedin_url : `https://${meta.linkedin_url}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center px-2 py-0.5 rounded border border-border bg-zinc-950 hover:text-zinc-200"
            >
              <Linkedin className="w-3 h-3 mr-1 text-zinc-500" />
              LinkedIn
            </a>
          )}
          {meta.github_url && (
            <a
              href={meta.github_url.startsWith("http") ? meta.github_url : `https://${meta.github_url}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center px-2 py-0.5 rounded border border-border bg-zinc-950 hover:text-zinc-200"
            >
              <Github className="w-3 h-3 mr-1 text-zinc-500" />
              GitHub
            </a>
          )}
        </div>
      </div>

      {/* Raw text */}
      {showRaw && (
        <div className="p-4 rounded-xl border border-border bg-zinc-950 space-y-2">
          <div className="text-[11px] font-mono uppercase text-zinc-500">Raw Text</div>
          <pre className="text-xs text-zinc-300 font-mono whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed bg-surface p-3 rounded-lg border border-border">
            {cand.raw_text}
          </pre>
        </div>
      )}

      {/* Experience Timeline */}
      <div className="space-y-4">
        <div className="text-xs font-mono uppercase text-zinc-500">
          Work Experiences ({experiences.length})
        </div>

        <div className="border-l border-border ml-3 pl-5 space-y-6">
          {experiences.map((exp, idx) => {
            const hasImpacts = exp.impact_metrics && exp.impact_metrics.length > 0;

            return (
              <div key={idx} className="relative space-y-2">
                <div className="absolute -left-[25px] top-1.5 w-2.5 h-2.5 rounded-full bg-zinc-800 border border-zinc-600" />

                <div className="p-4 rounded-xl border border-border bg-surface space-y-2.5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="text-sm font-semibold text-zinc-100">{exp.job_title}</h3>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border bg-zinc-900 text-zinc-400">
                          {exp.seniority_level || "Mid"}
                        </span>
                        {exp.is_current && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-border bg-zinc-900 text-zinc-300">
                            Current
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-zinc-400 mt-0.5">
                        {exp.company} • Standardized: {exp.standardized_role}
                      </div>
                    </div>

                    <div className="text-xs text-zinc-500 font-mono flex items-center">
                      <Calendar className="w-3 h-3 mr-1" />
                      <span>{exp.start_date || "Start"} – {exp.end_date || (exp.is_current ? "Present" : "End")}</span>
                      <span className="ml-1.5 text-zinc-400">({exp.duration_months} mos)</span>
                    </div>
                  </div>

                  {/* Quantified STAR impacts */}
                  {hasImpacts && (
                    <div className="space-y-1 pt-1">
                      <div className="text-[10px] font-mono uppercase text-zinc-500">STAR Metrics</div>
                      <div className="space-y-1">
                        {exp.impact_metrics.map((m, mIdx) => (
                          <div
                            key={mIdx}
                            className="flex items-start text-xs text-zinc-300 bg-zinc-950 px-2.5 py-1.5 rounded-md border border-border"
                          >
                            <span className="px-1 py-0.2 rounded text-[10px] font-mono uppercase mr-2 shrink-0 bg-zinc-900 text-zinc-400 border border-border">
                              {m.metric_type}
                            </span>
                            <span>{m.raw_statement}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-zinc-400 leading-relaxed pt-1">
                    {exp.experience_narrative}
                  </p>

                  {/* Tech stack */}
                  {exp.technologies_used && exp.technologies_used.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1 border-t border-border/60">
                      {exp.technologies_used.map((t, tIdx) => (
                        <span
                          key={tIdx}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-950 text-zinc-400 border border-border"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Education */}
      {education.length > 0 && (
        <div className="space-y-3 pt-2">
          <div className="text-xs font-mono uppercase text-zinc-500">Education</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {education.map((edu: any, idx: number) => (
              <div key={idx} className="p-3.5 rounded-xl border border-border bg-surface">
                <h3 className="font-medium text-xs text-zinc-200">{edu.institution}</h3>
                <p className="text-xs text-zinc-400 mt-0.5">
                  {edu.degree} {edu.field_of_study ? `in ${edu.field_of_study}` : ""}
                </p>
                {edu.graduation_year && (
                  <p className="text-[11px] text-zinc-500 font-mono mt-0.5">Year: {edu.graduation_year}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
