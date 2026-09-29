"use client";
import { useState, useRef, useEffect } from "react";
import type { Turn } from "@/lib/useSSE";
import AgentMessage from "./AgentMessage";
import ProposalDownload from "./ProposalDownload";
import { JarMark } from "./icons";

interface ChatWindowProps {
  turns: Turn[];
  isStreaming: boolean;
  proposalSessionId: string;
  sendMessage: (message: string, sessionId: string) => Promise<void>;
}

export default function ChatWindow({
  turns,
  isStreaming,
  proposalSessionId,
  sendMessage,
}: ChatWindowProps) {
  const [input, setInput] = useState("");
  const [sessionId] = useState(() => crypto.randomUUID());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    const msg = input;
    setInput("");
    await sendMessage(msg, sessionId);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <div className="flex flex-col flex-1 min-h-0 md:h-screen overflow-hidden bg-ground">
      <header className="border-b border-brass/30 px-6 py-4 bg-surface flex-shrink-0 flex items-center gap-3">
        <JarMark className="w-5 h-6 text-amber flex-shrink-0" />
        <div>
          <h1 className="font-display text-lg text-ink leading-tight">Keystone</h1>
          <p className="text-xs text-ink-soft">Multi-agent AI · LangChain · RAG · GPT-4o</p>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {turns.length === 0 && !isStreaming && (
          <div className="text-center mt-20 max-w-md mx-auto">
            <JarMark className="w-8 h-10 mx-auto mb-4 text-brass/60" />
            <p className="font-display text-lg text-ink mb-4">What can I compound for you?</p>
            <div className="text-sm space-y-2 text-ink-soft">
              <p className="italic">&quot;What deadlines do I have this week?&quot;</p>
              <p className="italic">&quot;Show me open PRs for Project Alpha&quot;</p>
              <p className="italic">&quot;What&apos;s the status of Project Beta?&quot;</p>
            </div>
          </div>
        )}

        {turns.map((turn, i) => (
          <div key={i} className="mb-6 max-w-3xl mx-auto">
            <div className="flex justify-end mb-3">
              <div className="bg-ink text-surface rounded-sm px-4 py-2 text-sm max-w-[75%]">
                {turn.userMessage}
              </div>
            </div>

            {turn.events.map((event, j) => (
              <div key={j}>
                <AgentMessage agent={event.agent} type={event.type} content={event.content} />
                {turn.source === "proposal" &&
                  event.agent === "producer" &&
                  event.type === "final" &&
                  proposalSessionId && <ProposalDownload sessionId={proposalSessionId} />}
              </div>
            ))}
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-brass/30 p-4 bg-surface flex-shrink-0"
      >
        <div className="max-w-3xl mx-auto flex gap-3 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about deadlines, repos, or project status… (Enter to send)"
            rows={2}
            className="flex-1 rounded-sm border border-brass/40 bg-ground px-4 py-2 text-sm text-ink placeholder:text-ink-soft/70 focus:outline-none resize-none"
            disabled={isStreaming}
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="rounded-sm bg-amber text-surface px-5 py-2 text-sm font-medium hover:bg-amber-deep disabled:opacity-40 disabled:hover:bg-amber transition-colors h-[42px]"
          >
            {isStreaming ? "Compounding…" : "Dispense"}
          </button>
        </div>
      </form>
    </div>
  );
}
