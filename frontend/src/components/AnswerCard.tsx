import type { QueryResult } from "@/types";
import { SourceBadge } from "./SourceBadge";

interface AnswerCardProps {
  question: string;
  result: QueryResult;
}

export function AnswerCard({ question, result }: AnswerCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="bg-gray-50 border-b border-gray-200 px-5 py-3">
        <p className="text-sm font-medium text-gray-600">Q:</p>
        <p className="text-gray-900 font-medium">{question}</p>
      </div>

      <div className="px-5 py-4">
        <p className="text-sm font-medium text-gray-600 mb-2">A:</p>
        <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap">
          {result.answer}
        </div>

        {result.sources.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Sources used
            </p>
            <div className="grid gap-2">
              {result.sources.map((src, i) => (
                <SourceBadge key={i} source={src} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
