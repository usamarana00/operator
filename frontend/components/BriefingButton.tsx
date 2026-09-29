"use client";

import { useState } from "react";
import { useBackendToken } from "@/lib/useBackendToken";
import { SunriseIcon } from "./icons";

interface BriefingButtonProps {
  onStream: (chunks: string) => void;
}

export default function BriefingButton({ onStream }: BriefingButtonProps) {
  const { getToken } = useBackendToken();
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (loading) return;
    setLoading(true);

    try {
      onStream("");
      const token = await getToken();
      const res = await fetch("/api/backend/briefing", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok || !res.body) {
        throw new Error("Briefing request failed");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });
        onStream(accumulated);
      }
    } catch (err) {
      console.error("BriefingButton: stream error", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-sm text-sm font-medium transition-colors text-ink-soft hover:text-ink hover:bg-surface disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <SunriseIcon className={`w-4 h-4 flex-shrink-0 ${loading ? "animate-pulse" : ""}`} />
      <span>{loading ? "Compounding briefing..." : "Morning Briefing"}</span>
    </button>
  );
}
