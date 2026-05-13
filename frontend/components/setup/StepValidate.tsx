"use client";
import { useState } from "react";

const BACKEND = "/api/backend";

type Props = {
  token: string;
  onNext: () => void;
};

export default function StepValidate({ token, onNext }: Props) {
  const [key, setKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    if (!key.trim().startsWith("sk-")) {
      setError("Key must start with sk-");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`${BACKEND}/setup/keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ openai_key: key.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to save key");
      }
      setSaved(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-1">Add your OpenAI key</h2>
      <p className="text-sm text-gray-500 mb-6">
        Your GitHub account is already connected. We just need your OpenAI API key — it
        will be encrypted and stored securely, never shared.
      </p>

      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-600 mb-1.5">
          OpenAI API Key
        </label>
        <input
          type="password"
          placeholder="sk-proj-..."
          value={key}
          onChange={(e) => { setKey(e.target.value); setSaved(false); setError(""); }}
          className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="text-xs text-gray-400 mt-1">
          Get yours at{" "}
          <a
            href="https://platform.openai.com/api-keys"
            target="_blank"
            rel="noreferrer"
            className="text-blue-500 underline"
          >
            platform.openai.com/api-keys
          </a>
        </p>
      </div>

      {error && (
        <p className="text-xs text-red-600 mb-3">{error}</p>
      )}

      {saved && (
        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2 mb-4">
          <span>✓</span> Key saved securely
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving || !key.trim()}
          className="flex-1 py-2.5 bg-gray-800 text-white rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-40 transition-colors"
        >
          {saving ? "Saving…" : saved ? "Saved ✓" : "Save key"}
        </button>
        <button
          onClick={onNext}
          disabled={!saved}
          className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
        >
          Next — Select repos →
        </button>
      </div>
    </div>
  );
}
