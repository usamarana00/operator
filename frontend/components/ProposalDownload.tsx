"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";

interface ProposalDownloadProps {
  sessionId: string;
}

export default function ProposalDownload({ sessionId }: ProposalDownloadProps) {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken as string | undefined;
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    if (loading) return;
    setLoading(true);

    try {
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
      className="mt-2 flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-900 hover:bg-gray-700 text-white transition-colors disabled:opacity-50"
    >
      <span>{loading ? "..." : "PDF"}</span>
      <span>{loading ? "Generating PDF..." : "Download as PDF"}</span>
    </button>
  );
}
