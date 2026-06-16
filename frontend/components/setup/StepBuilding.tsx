import { useEffect, useRef, useState } from "react";
import { ProjectConfig } from "./types";

const BACKEND = "/api/backend";

type Props = {
  projects: ProjectConfig[];
  token: string;
  onComplete: () => void;
};

type LogLine = { text: string; done: boolean };

export default function StepBuilding({ projects, token, onComplete }: Props) {
  const [log, setLog] = useState<LogLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [log]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const payload = {
      projects: projects.map((p) => ({
        name: p.name,
        client: p.client,
        repo_owner: p.repo.owner,
        repo_name: p.repo.repo_name,
        milestones: p.milestones.filter((m) => m.title && m.due_date),
      })),
    };

    (async () => {
      try {
        const res = await fetch(`${BACKEND}/setup/complete`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        });

        if (!res.body) throw new Error("No response body");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done: streamDone, value } = await reader.read();
          if (streamDone) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === "done") {
                setLog((prev) => [...prev, { text: event.content, done: true }]);
                setDone(true);
              } else if (event.type === "progress") {
                setLog((prev) => [...prev, { text: event.content, done: false }]);
              } else if (event.type === "error") {
                setError(event.content);
              }
            } catch {
              // skip malformed events
            }
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error");
      }
    })();
  }, []);

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-1">
        {done ? "Setup Complete" : "Building Knowledge Base..."}
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        {done
          ? "Your projects have been indexed. The AI is ready."
          : "Fetching READMEs, seeding the database, and building the vector index."}
      </p>

      <div className="bg-gray-950 rounded-lg p-4 h-56 overflow-y-auto font-mono text-xs mb-4">
        {log.map((line, i) => (
          <div key={i} className={`mb-1 ${line.done ? "text-green-400" : "text-gray-300"}`}>
            <span className="text-gray-600 mr-2">›</span>
            {line.text}
          </div>
        ))}
        {!done && !error && (
          <div className="text-gray-500 animate-pulse">working...</div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
          Error: {error}
        </div>
      )}

      <button
        disabled={!done}
        onClick={onComplete}
        className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-40 transition-colors"
      >
        Open the assistant
      </button>
    </div>
  );
}
