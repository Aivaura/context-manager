"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { queryApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { QueryBox } from "@/components/QueryBox";
import { AnswerCard } from "@/components/AnswerCard";
import type { QueryResult } from "@/types";

interface QAPair {
  question: string;
  result: QueryResult;
}

export default function AskPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const [history, setHistory] = useState<QAPair[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) router.push("/login");
  }, [token, router]);

  const handleQuestion = async (question: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await queryApi.ask(question);
      setHistory((prev) => [{ question, result }, ...prev]);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to get answer. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (!token) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-700">
            ← Back to dashboard
          </Link>
          <h1 className="font-semibold text-gray-900">Ask your company knowledge</h1>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <QueryBox
            onSubmit={handleQuestion}
            loading={loading}
            placeholder="What do you want to know about your company data?"
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-5 py-4 text-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="flex flex-col items-center gap-3 text-gray-400">
              <svg className="h-8 w-8 animate-spin text-brand-500" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <p className="text-sm">Searching your knowledge base...</p>
            </div>
          </div>
        )}

        {history.length === 0 && !loading && !error && (
          <div className="text-center py-16 text-gray-400">
            <p className="text-4xl mb-4">💬</p>
            <p className="font-medium text-gray-600">Ask anything about your company</p>
            <p className="text-sm mt-1">
              Try: &ldquo;What was our last quote to a client?&rdquo; or &ldquo;Who is our contact at [company]?&rdquo;
            </p>
          </div>
        )}

        <div className="space-y-6">
          {history.map((pair, i) => (
            <AnswerCard key={i} question={pair.question} result={pair.result} />
          ))}
        </div>
      </main>
    </div>
  );
}
