"use client";

import { useState } from "react";
import { connectorsApi } from "@/lib/api";
import type { Connector } from "@/types";
import { StatusBadge } from "./StatusBadge";

const META: Record<string, { label: string; description: string }> = {
  gmail: {
    label: "Gmail",
    description: "Index emails from your Gmail inbox.",
  },
  google_drive: {
    label: "Google Drive",
    description: "Index documents, PDFs, and files from Drive.",
  },
  outlook: {
    label: "Microsoft Outlook",
    description: "Index emails via Microsoft Graph API.",
  },
  whatsapp: {
    label: "WhatsApp Business",
    description: "Index messages via Meta webhook.",
  },
  sheets: {
    label: "Google Sheets / Excel",
    description: "Index spreadsheet data from Sheets or uploaded Excel files.",
  },
};

interface ConnectorCardProps {
  connector: Connector;
  onRefresh: () => void;
}

export function ConnectorCard({ connector, onRefresh }: ConnectorCardProps) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const meta = META[connector.type] || { label: connector.type, description: "" };

  const handleConnect = async () => {
    setLoading(true);
    try {
      const data = await connectorsApi.getAuthUrl(connector.type);
      if (data.url) {
        window.location.href = data.url;
      } else if (data.message) {
        setMessage(`Webhook URL: ${data.webhook_url}\nVerify Token: ${data.verify_token}`);
      }
    } catch {
      setMessage("Failed to get auth URL");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setLoading(true);
    try {
      await connectorsApi.sync(connector.type);
      setMessage("Sync started...");
      setTimeout(onRefresh, 3000);
    } catch {
      setMessage("Sync failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm(`Disconnect ${meta.label}? All indexed data will be removed.`)) return;
    setLoading(true);
    try {
      await connectorsApi.disconnect(connector.type);
      onRefresh();
    } catch {
      setMessage("Disconnect failed");
    } finally {
      setLoading(false);
    }
  };

  const isConnected = connector.status === "connected";
  const isSyncing = connector.status === "syncing";

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <h3 className="font-semibold text-gray-900">{meta.label}</h3>
            <StatusBadge status={connector.status} />
          </div>
          <p className="text-sm text-gray-500">{meta.description}</p>
          {isConnected && (
            <p className="text-xs text-gray-400 mt-1">
              {connector.document_count.toLocaleString()} items indexed
              {connector.last_sync_at && ` · Last synced: ${new Date(connector.last_sync_at).toLocaleTimeString()}`}
            </p>
          )}
          {connector.error_message && (
            <p className="text-xs text-red-600 mt-1">Error: {connector.error_message}</p>
          )}
          {message && (
            <pre className="text-xs text-blue-700 bg-blue-50 rounded p-2 mt-2 whitespace-pre-wrap">
              {message}
            </pre>
          )}
        </div>

        <div className="flex gap-2 shrink-0">
          {!isConnected && !isSyncing && (
            <button
              onClick={handleConnect}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50 transition-colors"
            >
              Connect →
            </button>
          )}
          {isConnected && (
            <>
              <button
                onClick={handleSync}
                disabled={loading}
                className="px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50 transition-colors"
              >
                Sync now
              </button>
              <button
                onClick={handleDisconnect}
                disabled={loading}
                className="px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50 transition-colors"
              >
                Disconnect
              </button>
            </>
          )}
          {isSyncing && (
            <span className="px-3 py-2 text-sm text-yellow-600 animate-pulse">
              Syncing...
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
