interface StatusBadgeProps {
  status: "connected" | "disconnected" | "syncing" | "error";
}

const config = {
  connected: { dot: "bg-green-500", text: "text-green-700", label: "Connected" },
  syncing: { dot: "bg-yellow-400 animate-pulse", text: "text-yellow-700", label: "Syncing..." },
  error: { dot: "bg-red-500", text: "text-red-700", label: "Error" },
  disconnected: { dot: "bg-gray-300", text: "text-gray-500", label: "Not connected" },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const c = config[status] || config.disconnected;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-2 w-2 rounded-full ${c.dot}`} />
      <span className={`text-sm font-medium ${c.text}`}>{c.label}</span>
    </span>
  );
}
