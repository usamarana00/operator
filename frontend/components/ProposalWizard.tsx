"use client";

import { useState } from "react";
import { useBackendToken } from "@/lib/useBackendToken";

interface ProposalWizardProps {
  open: boolean;
  onClose: () => void;
  onStream: (chunks: string) => void;
  onSessionId: (id: string) => void;
}

export default function ProposalWizard({
  open,
  onClose,
  onStream,
  onSessionId,
}: ProposalWizardProps) {
  const { getToken } = useBackendToken();
  const [client, setClient] = useState("");
  const [description, setDescription] = useState("");
  const [budget, setBudget] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!client.trim() || !description.trim()) {
      setError("Client and description are required.");
      return;
    }

    setError("");
    setLoading(true);
    onClose();

    try {
      const sessionId = crypto.randomUUID();
      onSessionId(sessionId);
      onStream("");

      const token = await getToken();
      const res = await fetch("/api/backend/proposal", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ client, description, budget, session_id: sessionId }),
      });

      if (!res.ok || !res.body) {
        throw new Error("Proposal request failed");
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
      console.error("ProposalWizard: stream error", err);
    } finally {
      setLoading(false);
      setClient("");
      setDescription("");
      setBudget("");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
      <div className="bg-surface border border-brass/40 rounded-sm shadow-xl w-full max-w-md p-6">
        <h2 className="font-display text-lg text-ink mb-4">Prepare a Label</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs text-ink-soft mb-1">Client name *</label>
            <input
              type="text"
              value={client}
              onChange={(event) => setClient(event.target.value)}
              placeholder="e.g. Acme Corp"
              className="w-full bg-ground border border-brass/40 text-ink rounded-sm px-3 py-2 text-sm outline-none focus-visible:border-amber-deep"
            />
          </div>
          <div>
            <label className="block text-xs text-ink-soft mb-1">Project description *</label>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe what needs to be built..."
              rows={4}
              className="w-full bg-ground border border-brass/40 text-ink rounded-sm px-3 py-2 text-sm outline-none focus-visible:border-amber-deep resize-none"
            />
          </div>
          <div>
            <label className="block text-xs text-ink-soft mb-1">Budget range</label>
            <input
              type="text"
              value={budget}
              onChange={(event) => setBudget(event.target.value)}
              placeholder="e.g. $3,000-$5,000"
              className="w-full bg-ground border border-brass/40 text-ink rounded-sm px-3 py-2 text-sm outline-none focus-visible:border-amber-deep"
            />
          </div>
          {error && <p className="text-carmine text-sm">{error}</p>}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-sm text-sm text-ink-soft hover:text-ink hover:bg-ground transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-sm text-sm font-medium bg-amber hover:bg-amber-deep text-surface transition-colors disabled:opacity-50"
            >
              {loading ? "Compounding..." : "Prepare Proposal"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
