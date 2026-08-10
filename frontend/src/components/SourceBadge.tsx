import type { Source } from "@/types";

const icons: Record<string, string> = {
  gmail: "📧",
  google_drive: "📄",
  outlook: "📬",
  whatsapp: "💬",
  sheets: "📊",
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

interface SourceBadgeProps {
  source: Source;
}

export function SourceBadge({ source }: SourceBadgeProps) {
  const icon = icons[source.source_type] || "📎";
  const parts = [
    source.source_type.replace("_", " "),
    source.author,
    formatDate(source.date),
  ].filter(Boolean);

  return (
    <div className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-3 text-sm">
      <span className="text-lg">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">
          {source.title || parts[0]}
        </p>
        <p className="text-gray-500 text-xs mt-0.5">{parts.join(" · ")}</p>
        {source.snippet && (
          <p className="text-gray-600 text-xs mt-1 line-clamp-2">{source.snippet}</p>
        )}
      </div>
      {source.url && (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-brand-600 hover:underline text-xs"
        >
          View →
        </a>
      )}
    </div>
  );
}
