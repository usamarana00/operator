"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";

interface BriefingButtonProps {
  onStream: (chunks: string) => void;
}

export default function BriefingButton({ onStream }: BriefingButtonProps) {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken as string | undefined;
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (loading) return;
    setLoading(true);

    try {
      onStream("");
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
      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-gray-600 hover:text-gray-900 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <span>{loading ? "..." : "Sun"}</span>
      <span>{loading ? "Generating briefing..." : "Morning Briefing"}</span>
    </button>
  );
}
