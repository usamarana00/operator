"use client";
import { useState, useRef } from "react";
import { useBackendToken } from "@/lib/useBackendToken";
import { UploadIcon, CheckIcon, AlertIcon } from "./icons";

interface Props {
  projectId: string;
  onUploaded?: (file: { id: string; filename: string; size_bytes: number }) => void;
}

type UploadState = "idle" | "uploading" | "done" | "error";

const BACKEND = "/api/backend";

export default function FileUpload({ projectId, onUploaded }: Props) {
  const { getToken } = useBackendToken();
  const [state, setState] = useState<UploadState>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function upload(file: File) {
    const token = await getToken();
    if (!token) return;
    setState("uploading");
    setProgress(0);
    setError("");

    try {
      // 1. Request presigned PUT URL from backend
      const presignRes = await fetch(`${BACKEND}/files/presign`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          project_id: projectId,
          filename: file.name,
          content_type: file.type || "application/octet-stream",
        }),
      });

      if (!presignRes.ok) throw new Error("Failed to get upload URL");
      const { file_id, upload_url } = await presignRes.json();

      // 2. PUT directly to S3 — backend never sees the bytes
      const xhr = new XMLHttpRequest();
      await new Promise<void>((resolve, reject) => {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
        };
        xhr.onload = () => (xhr.status < 300 ? resolve() : reject(new Error(`S3 ${xhr.status}`)));
        xhr.onerror = () => reject(new Error("Upload failed"));
        xhr.open("PUT", upload_url);
        xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
        xhr.send(file);
      });

      setProgress(100);

      // 3. Confirm metadata to backend
      const confirmRes = await fetch(`${BACKEND}/files/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          file_id,
          project_id: projectId,
          filename: file.name,
          content_type: file.type || "application/octet-stream",
          size_bytes: file.size,
        }),
      });

      if (!confirmRes.ok) throw new Error("Failed to save file metadata");
      const saved = await confirmRes.json();

      setState("done");
      onUploaded?.({ id: saved.id, filename: saved.filename, size_bytes: saved.size_bytes });

      // Reset after 2s
      setTimeout(() => {
        setState("idle");
        setProgress(0);
        if (inputRef.current) inputRef.current.value = "";
      }, 2000);
    } catch (err: any) {
      setState("error");
      setError(err.message ?? "Upload failed");
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) upload(file);
  }

  return (
    <div className="flex flex-col gap-2">
      <label
        className={`flex items-center gap-2 cursor-pointer border-2 border-dashed rounded-sm px-4 py-3 text-sm transition-colors
          ${state === "uploading" ? "border-amber/50 bg-amber-glow/10" : "border-brass/40 hover:border-brass bg-surface"}`}
      >
        <input
          ref={inputRef}
          type="file"
          className="sr-only"
          onChange={handleChange}
          disabled={state === "uploading"}
        />
        {state === "idle" && (
          <>
            <UploadIcon className="w-4 h-4 text-ink-soft" />
            <span className="text-ink-soft">Attach a file</span>
          </>
        )}
        {state === "uploading" && (
          <>
            <UploadIcon className="w-4 h-4 text-amber-deep animate-pulse" />
            <span className="text-amber-deep tabular">Uploading… {progress}%</span>
          </>
        )}
        {state === "done" && (
          <>
            <CheckIcon className="w-4 h-4 text-moss" />
            <span className="text-moss">Uploaded</span>
          </>
        )}
        {state === "error" && (
          <>
            <AlertIcon className="w-4 h-4 text-carmine" />
            <span className="text-carmine truncate">{error}</span>
          </>
        )}
      </label>

      {state === "uploading" && (
        <div className="h-1 w-full bg-surface-recessed rounded-full overflow-hidden">
          <div
            className="h-full bg-amber transition-all duration-200"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
