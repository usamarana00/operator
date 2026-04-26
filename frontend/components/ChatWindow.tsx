"use client";
import { useState, useRef, useEffect } from "react";
import { useSSE } from "@/lib/useSSE";
import AgentMessage from "./AgentMessage";

export default function ChatWindow() {
  const [input, setInput] = useState("");
  const [sessionId] = useState(() => crypto.randomUUID());
  const { events, isStreaming, sendMessage } = useSSE();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

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
    <div className="flex flex-col flex-1 h-screen overflow-hidden">
      <header className="border-b border-gray-200 px-6 py-4 bg-white flex-shrink-0">
        <h1 className="text-lg font-semibold text-gray-800">Freelance Project Assistant</h1>
        <p className="text-xs text-gray-400">Multi-agent AI · LangGraph · RAG · GPT-4o</p>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {events.length === 0 && !isStreaming && (
          <div className="text-center text-gray-400 text-sm mt-20 space-y-2">
            <p className="text-2xl">🤖</p>
            <p className="font-medium text-gray-500">What can I help you with?</p>
            <div className="text-xs space-y-1 text-gray-400">
              <p>&quot;What deadlines do I have this week?&quot;</p>
              <p>&quot;Show me open PRs for Project Alpha&quot;</p>
              <p>&quot;What&apos;s the status of Project Beta?&quot;</p>
            </div>
          </div>
        )}
        {events.map((event, i) => (
          <AgentMessage key={i} agent={event.agent} type={event.type} content={event.content} />
        ))}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-gray-200 p-4 bg-white flex-shrink-0 flex gap-3 items-end"
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about deadlines, repos, or project status... (Enter to send)"
          rows={2}
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          disabled={isStreaming}
        />
        <button
          type="submit"
          disabled={isStreaming || !input.trim()}
          className="rounded-lg bg-blue-600 text-white px-5 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors h-[42px]"
        >
          {isStreaming ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
