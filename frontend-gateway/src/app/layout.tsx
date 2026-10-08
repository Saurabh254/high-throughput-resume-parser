import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "HyperATS - High-Performance ATS Parser & Semantic Matcher",
  description:
    "High-performance local ATS parser with pgvector cosine ANN search, BERT cross-encoder reranking, and deep work experience trajectory matching.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col bg-background text-zinc-100 antialiased selection:bg-zinc-800 selection:text-zinc-100">
        <Navbar />
        <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
