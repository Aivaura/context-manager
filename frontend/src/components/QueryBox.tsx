"use client";

import { useState } from "react";

interface QueryBoxProps {
  onSubmit: (question: string) => void;
  loading: boolean;
  placeholder?: string;
}

export function QueryBox({ onSubmit, loading, placeholder = "What do you want to know?" }: QueryBoxProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = value.trim();
    if (!q || loading) return;
    onSubmit(q);
    setValue("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        disabled={loading}
        className="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 disabled:opacity-50 transition-shadow"
      />
      <button
        type="submit"
        disabled={loading || !value.trim()}
        className="px-6 py-3 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Thinking...
          </span>
        ) : (
          "Ask"
        )}
      </button>
    </form>
  );
}
