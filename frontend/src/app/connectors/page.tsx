"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { connectorsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { ConnectorCard } from "@/components/ConnectorCard";

export default function ConnectorsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!token) router.push("/login");
  }, [token, router]);

  const connected = searchParams.get("connected");
  const error = searchParams.get("error");

  const { data: connectors = [], refetch } = useQuery({
    queryKey: ["connectors"],
    queryFn: connectorsApi.list,
    enabled: !!token,
    refetchInterval: 15_000,
  });

  const handleRefresh = () => {
    refetch();
    queryClient.invalidateQueries({ queryKey: ["connectors"] });
  };

  if (!token) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-700">
            ← Back to dashboard
          </Link>
          <h1 className="font-semibold text-gray-900">Connect your data sources</h1>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8 space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4 text-sm text-blue-700">
          We only <strong>read</strong> your data and never modify or send anything outside your infrastructure.
        </div>

        {connected && (
          <div className="bg-green-50 border border-green-200 rounded-xl px-5 py-4 text-sm text-green-700">
            ✓ {connected.replace("_", " ")} connected successfully. Starting initial sync...
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 text-sm text-red-700">
            Connection error: {error.replace(/_/g, " ")}
          </div>
        )}

        <div className="space-y-3">
          {connectors.map((connector) => (
            <ConnectorCard
              key={connector.type}
              connector={connector}
              onRefresh={handleRefresh}
            />
          ))}
        </div>

        <div className="bg-gray-100 rounded-xl px-5 py-4 text-xs text-gray-500">
          <p className="font-medium text-gray-600 mb-1">Excel / CSV file upload</p>
          <p>Upload spreadsheet files directly via the API endpoint:</p>
          <code className="block mt-1 font-mono text-xs bg-gray-200 rounded px-2 py-1">
            POST /api/v1/documents/upload — multipart form, field: file
          </code>
        </div>
      </main>
    </div>
  );
}
