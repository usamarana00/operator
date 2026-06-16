"use client";
import { useEffect, useState } from "react";

const BACKEND = "/api/backend";

type Props = {
  token: string;
  onNext: () => void;
};

export default function StepValidate({ token, onNext }: Props) {
  const [key, setKey] = useState("");
  const [checking, setChecking] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function checkExistingKey() {
      if (!token) {
        console.info("[setup] status check skipped: missing token");
        setChecking(false);
        return;
      }

      setChecking(true);
      try {
        console.info("[setup] status check requested", { hasToken: Boolean(token) });
        const res = await fetch(`${BACKEND}/setup/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json().catch(() => ({}));
        console.info("[setup] status response", {
          ok: res.ok,
          status: res.status,
          hasOpenaiKey: Boolean(data.has_openai_key),
          serverHasOpenaiKey: Boolean(data.server_has_openai_key),
          configured: Boolean(data.configured),
        });
        if (!cancelled && data.has_openai_key) {
          onNext();
        }
      } catch (err: any) {
        console.error("[setup] status check failed", {
          message: err?.message ?? "Unknown error",
        });
      } finally {
        if (!cancelled) setChecking(false);
      }
    }

    checkExistingKey();
    return () => {
      cancelled = true;
    };
  }, [token, onNext]);

  async function handleSave() {
    const trimmedKey = key.trim();
    if (!trimmedKey) {
      onNext();
      return;
    }

    if (!trimmedKey.startsWith("sk-")) {
      setError("Key must start with sk-");
      return;
    }

    setSaving(true);
    setError("");
    try {
      console.info("[setup] OpenAI key save requested", {
        hasToken: Boolean(token),
        keyPrefixValid: trimmedKey.startsWith("sk-"),
      });
      const res = await fetch(`${BACKEND}/setup/keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ openai_key: trimmedKey }),
      });
      const data = await res.json().catch(() => ({}));
      console.info("[setup] OpenAI key save response", {
        ok: res.ok,
        status: res.status,
        statusText: res.statusText,
      });
      if (!res.ok) {
        throw new Error(data.detail ?? "Failed to save key");
      }
      setSaved(true);
    } catch (err: any) {
      console.error("[setup] OpenAI key save failed", {
        message: err?.message ?? "Unknown error",
      });
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-1">Add your OpenAI key</h2>
      <p className="text-sm text-gray-500 mb-6">
        Your GitHub account is already connected. You can add an OpenAI API key now
        or continue with the server configuration.
      </p>

      {checking && (
        <div className="text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 mb-4">
          Checking existing configuration...
        </div>
      )}

      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-600 mb-1.5">
          OpenAI API Key <span className="font-normal text-gray-400">(optional)</span>
        </label>
        <input
          type="password"
          placeholder="sk-proj-..."
          value={key}
          onChange={(e) => {
            setKey(e.target.value);
            setSaved(false);
            setError("");
          }}
          className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm font-mono text-gray-950 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
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

      {error && <p className="text-xs text-red-600 mb-3">{error}</p>}

      {saved && (
        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2 mb-4">
          <span>OK</span> Key saved securely
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving || checking}
          className="flex-1 py-2.5 bg-gray-800 text-white rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-40 transition-colors"
        >
          {saving ? "Saving..." : saved ? "Saved" : key.trim() ? "Save key" : "Skip for now"}
        </button>
        <button
          onClick={onNext}
          disabled={checking}
          className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
        >
          Next - Select repos
        </button>
      </div>
    </div>
  );
}
