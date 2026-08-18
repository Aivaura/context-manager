"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

function timeAgo(dateStr: string): string {
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.round(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)} hours ago`;
  if (diff < 172800) return "Yesterday";
  return new Date(dateStr).toLocaleDateString();
}

export default function AdminPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const hasHydrated = useAuthStore((s) => s._hasHydrated);
  const [reindexing, setReindexing] = useState(false);
  const [reindexMsg, setReindexMsg] = useState<string | null>(null);

  useEffect(() => {
    if (hasHydrated && !token) router.push("/login");
  }, [hasHydrated, token, router]);

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: adminApi.stats,
    enabled: !!token,
  });

  const { data: logs = [], refetch: refetchLogs } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => adminApi.auditLogs(50),
    enabled: !!token,
  });

  const handleReindex = async () => {
    if (!confirm("This will re-sync all connected sources. Continue?")) return;
    setReindexing(true);
    try {
      await adminApi.reindex();
      setReindexMsg("Full re-index started for all connected sources.");
    } catch {
      setReindexMsg("Failed to start re-index.");
    } finally {
      setReindexing(false);
    }
  };

  if (!hasHydrated || !token) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-700">
            ← Back to dashboard
          </Link>
          <h1 className="font-semibold text-gray-900">Admin Panel</h1>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {stats && (
          <div>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              System Stats
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm text-center">
                <p className="text-3xl font-bold text-gray-900">
                  {stats.total_documents.toLocaleString()}
                </p>
                <p className="text-sm text-gray-500 mt-1">Documents indexed</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm text-center">
                <p className="text-3xl font-bold text-gray-900">
                  {stats.total_queries.toLocaleString()}
                </p>
                <p className="text-sm text-gray-500 mt-1">Queries answered</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm text-center">
                <p className="text-3xl font-bold text-gray-900">{stats.active_connectors} / 5</p>
                <p className="text-sm text-gray-500 mt-1">Active connectors</p>
              </div>
            </div>
          </div>
        )}

        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
              Recent activity log
            </h2>
            <button
              onClick={() => refetchLogs()}
              className="text-xs text-brand-600 hover:underline"
            >
              Refresh
            </button>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
            <div className="grid grid-cols-[1fr_2fr] text-xs font-semibold text-gray-500 uppercase tracking-wide px-5 py-3 border-b border-gray-100 bg-gray-50">
              <span>Time</span>
              <span>Query</span>
            </div>
            {logs.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">No queries yet</p>
            ) : (
              <div className="divide-y divide-gray-50">
                {logs.map((log) => (
                  <div
                    key={log.id}
                    className="grid grid-cols-[1fr_2fr] gap-4 px-5 py-3 text-sm hover:bg-gray-50"
                  >
                    <span className="text-gray-400 text-xs">{timeAgo(log.created_at)}</span>
                    <span className="text-gray-700 truncate">&ldquo;{log.query}&rdquo;</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div>
          <h2 className="text-sm font-semibold text-red-500 uppercase tracking-wide mb-4">
            Danger zone
          </h2>
          <div className="bg-white rounded-xl border border-red-200 p-5 shadow-sm space-y-4">
            {reindexMsg && (
              <p className="text-sm text-blue-700 bg-blue-50 rounded-lg px-3 py-2">{reindexMsg}</p>
            )}
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-800 text-sm">Re-index all data</p>
                <p className="text-xs text-gray-500">
                  Force a full re-sync of all connected sources.
                </p>
              </div>
              <button
                onClick={handleReindex}
                disabled={reindexing}
                className="px-4 py-2 text-sm font-medium text-red-600 border border-red-300 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
              >
                {reindexing ? "Starting..." : "Re-index all data"}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
