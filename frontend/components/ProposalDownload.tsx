"use client";

import { useState } from "react";
import { useBackendToken } from "@/lib/useBackendToken";
import { LabelIcon } from "./icons";

interface ProposalDownloadProps {
  sessionId: string;
}

export default function ProposalDownload({ sessionId }: ProposalDownloadProps) {
  const { getToken } = useBackendToken();
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    if (loading) return;
    setLoading(true);

    try {
      const token = await getToken();
      const res = await fetch(`/api/backend/proposal/${sessionId}/pdf`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        throw new Error("PDF generation failed");
      }

      const blob = await res.blob();
      const contentDisposition = res.headers.get("content-disposition") ?? "";
      const filenameMatch = contentDisposition.match(/filename="(.+?)"/);
      const filename =
        filenameMatch?.[1] ?? `proposal-${sessionId.slice(0, 8)}.pdf`;

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("ProposalDownload: error", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={loading}
      className="mt-2 flex items-center gap-2 px-3 py-1.5 rounded-sm text-xs font-medium bg-ink hover:bg-amber-deep text-surface transition-colors disabled:opacity-50"
    >
      <LabelIcon className="w-3.5 h-3.5" />
      <span>{loading ? "Sealing label..." : "Download as PDF"}</span>
    </button>
  );
}
