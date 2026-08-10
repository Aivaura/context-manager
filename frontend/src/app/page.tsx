"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { connectorsApi, queryApi, adminApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { StatusBadge } from "@/components/StatusBadge";
import type { Connector } from "@/types";

const CONNECTOR_LABELS: Record<string, string> = {
  gmail: "Gmail",
  google_drive: "Google Drive",
  outlook: "Outlook",
  whatsapp: "WhatsApp Business",
  sheets: "Google Sheets",
};

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.round(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)} hours ago`;
  return `${Math.round(diff / 86400)} days ago`;
}

export default function DashboardPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    if (!token) router.push("/login");
  }, [token, router]);

  const { data: connectors = [] } = useQuery({
    queryKey: ["connectors"],
    queryFn: connectorsApi.list,
    enabled: !!token,
    refetchInterval: 30_000,
  });

  const { data: history = [] } = useQuery({
    queryKey: ["query-history"],
    queryFn: () => queryApi.history(5),
    enabled: !!token,
  });

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: adminApi.stats,
    enabled: !!token,
  });

  const firstName = user?.email?.split("@")[0] || "there";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  if (!token) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <h1 className="text-lg font-bold text-gray-900">AIVAURA</h1>
          <div className="flex items-center gap-4">
            <Link
              href="/ask"
              className="px-4 py-2 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors"
            >
              Ask a question →
            </Link>
            <button
              onClick={async () => {
                const { authApi } = await import("@/lib/api");
                await authApi.logout();
                router.push("/login");
              }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            {greeting}, {firstName}.
          </h2>
          {stats && (
            <p className="text-sm text-gray-500 mt-1">
              {stats.total_documents.toLocaleString()} items indexed across {stats.active_connectors} sources ·{" "}
              {stats.total_queries} queries answered
            </p>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">
              Your knowledge sources
            </h3>
            <Link href="/connectors" className="text-sm text-brand-600 hover:underline">
              Manage →
            </Link>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 overflow-hidden shadow-sm">
            {connectors.map((c: Connector) => (
              <div key={c.type} className="flex items-center justify-between px-5 py-4">
                <div className="flex items-center gap-3">
                  <StatusBadge status={c.status} />
                  <span className="font-medium text-gray-800">
                    {CONNECTOR_LABELS[c.type] || c.type}
                  </span>
                  {c.document_count > 0 && (
                    <span className="text-sm text-gray-400">
                      {c.document_count.toLocaleString()} items
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-400">{timeAgo(c.last_sync_at)}</span>
                  {c.status === "disconnected" && (
                    <Link
                      href="/connectors"
                      className="text-xs font-medium text-brand-600 border border-brand-200 px-2 py-1 rounded-md hover:bg-brand-50"
                    >
                      Connect
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {history.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">
                Recent questions
              </h3>
              <Link href="/ask" className="text-sm text-brand-600 hover:underline">
                Ask new →
              </Link>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 overflow-hidden shadow-sm">
              {history.map((item) => (
                <div key={item.id} className="px-5 py-4 flex items-center justify-between gap-4">
                  <p className="text-sm text-gray-700 truncate flex-1">
                    &ldquo;{item.query}&rdquo;
                  </p>
                  <span className="text-xs text-gray-400 shrink-0">
                    {timeAgo(item.created_at)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-3 gap-4">
          <Link
            href="/ask"
            className="flex flex-col items-center justify-center gap-2 bg-white border border-gray-200 rounded-xl p-6 hover:border-brand-300 hover:bg-brand-50 transition-colors shadow-sm"
          >
            <span className="text-2xl">💬</span>
            <span className="text-sm font-medium text-gray-700">Ask a question</span>
          </Link>
          <Link
            href="/connectors"
            className="flex flex-col items-center justify-center gap-2 bg-white border border-gray-200 rounded-xl p-6 hover:border-brand-300 hover:bg-brand-50 transition-colors shadow-sm"
          >
            <span className="text-2xl">🔌</span>
            <span className="text-sm font-medium text-gray-700">Manage connectors</span>
          </Link>
          <Link
            href="/admin"
            className="flex flex-col items-center justify-center gap-2 bg-white border border-gray-200 rounded-xl p-6 hover:border-brand-300 hover:bg-brand-50 transition-colors shadow-sm"
          >
            <span className="text-2xl">🛡️</span>
            <span className="text-sm font-medium text-gray-700">Admin panel</span>
          </Link>
        </div>
      </main>
    </div>
  );
}
