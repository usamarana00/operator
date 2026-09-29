import { useEffect, useRef, useState } from "react";
import { ProjectConfig } from "./types";
import { CheckIcon, AlertIcon } from "@/components/icons";

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
      <h2 className="font-display text-lg text-ink mb-1 flex items-center gap-2">
        {done && <CheckIcon className="w-4 h-4 text-moss" />}
        {done ? "Compounded" : "Compounding the Shelf…"}
      </h2>
      <p className="text-sm text-ink-soft mb-4">
        {done
          ? "Your projects have been indexed. Keystone is ready."
          : "Fetching READMEs, seeding the database, and building the vector index."}
      </p>

      <div className="bg-ink rounded-sm p-4 h-56 overflow-y-auto font-mono text-xs mb-4">
        {log.map((line, i) => (
          <div key={i} className={`mb-1 ${line.done ? "text-amber-glow" : "text-surface/70"}`}>
            <span className="text-brass mr-2">›</span>
            {line.text}
          </div>
        ))}
        {!done && !error && (
          <div className="text-surface/50 animate-pulse">measuring...</div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="bg-carmine-bg border border-carmine/30 rounded-sm p-3 mb-4 text-sm text-carmine flex items-center gap-2">
          <AlertIcon className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <button
        disabled={!done}
        onClick={onComplete}
        className="w-full py-2.5 bg-amber text-surface rounded-sm text-sm font-medium hover:bg-amber-deep disabled:opacity-40 transition-colors"
      >
        Open the counter
      </button>
    </div>
  );
}
