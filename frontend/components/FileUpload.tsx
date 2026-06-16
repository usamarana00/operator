"use client";
import { useState, useRef } from "react";
import { useSession } from "next-auth/react";

interface Props {
  projectId: string;
  onUploaded?: (file: { id: string; filename: string; size_bytes: number }) => void;
}

type UploadState = "idle" | "uploading" | "done" | "error";

const BACKEND = "/api/backend";

export default function FileUpload({ projectId, onUploaded }: Props) {
  const { data: session } = useSession();
  const [state, setState] = useState<UploadState>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const token = (session as any)?.accessToken as string | undefined;

  async function upload(file: File) {
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
        className={`flex items-center gap-2 cursor-pointer border-2 border-dashed rounded-xl px-4 py-3 text-sm transition-colors
          ${state === "uploading" ? "border-blue-300 bg-blue-50" : "border-gray-200 hover:border-gray-300 bg-white"}`}
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
            <span className="text-gray-400">📎</span>
            <span className="text-gray-500">Attach a file</span>
          </>
        )}
        {state === "uploading" && (
          <>
            <span className="text-blue-500">⬆</span>
            <span className="text-blue-600">Uploading… {progress}%</span>
          </>
        )}
        {state === "done" && (
          <>
            <span className="text-green-500">✓</span>
            <span className="text-green-600">Uploaded</span>
          </>
        )}
        {state === "error" && (
          <>
            <span className="text-red-500">✕</span>
            <span className="text-red-600 truncate">{error}</span>
          </>
        )}
      </label>

      {state === "uploading" && (
        <div className="h-1 w-full bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-400 transition-all duration-200"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
