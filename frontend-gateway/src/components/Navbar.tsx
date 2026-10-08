"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Layers, UploadCloud, Search, Activity } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch("/api/health");
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        }
      } catch (e) {
        // silent
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { href: "/", label: "Overview" },
    { href: "/upload", label: "Upload" },
    { href: "/search", label: "Search" },
  ];

  const allHealthy =
    health?.services?.ingestion?.status === "healthy" &&
    health?.services?.orchestrator?.status === "healthy";

  return (
    <nav className="border-b border-border bg-background/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center space-x-6">
            <Link href="/" className="flex items-center space-x-2.5 group">
              <div className="w-7 h-7 rounded-md bg-zinc-900 border border-border flex items-center justify-center text-zinc-200 group-hover:border-zinc-700 transition-colors">
                <Layers className="w-3.5 h-3.5 text-zinc-300" />
              </div>
              <span className="font-semibold text-sm text-zinc-100 tracking-tight">HyperATS</span>
              <span className="text-[10px] text-zinc-500 font-mono px-1.5 py-0.5 rounded border border-border bg-surface">
                pgvector
              </span>
            </Link>

            <div className="flex items-center space-x-1">
              {navLinks.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? "text-zinc-100 bg-zinc-900 border border-zinc-800"
                        : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50"
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="flex items-center space-x-3 text-xs text-zinc-500 font-mono">
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md border border-border bg-surface text-[11px]">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  allHealthy ? "bg-emerald-500" : "bg-amber-500"
                }`}
              />
              <span className="text-zinc-400">Services</span>
              <span className="text-zinc-600">•</span>
              <span className="text-zinc-500">HNSW 384d</span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
