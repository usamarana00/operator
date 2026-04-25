"use client";
import { useState, useCallback } from "react";

export type AgentEvent = {
  agent: string;
  type: string;
  content: string;
};

export function useSSE() {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(async (message: string, sessionId: string) => {
    setEvents([]);
    setIsStreaming(true);

    try {
      const response = await fetch("/api/backend/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: sessionId }),
      });

      if (!response.body) {
        setIsStreaming(false);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event: AgentEvent = JSON.parse(line.slice(6));
              if (event.type !== "done") {
                setEvents((prev) => [...prev, event]);
              }
            } catch {
              // skip malformed events
            }
          }
        }
      }
    } catch (error) {
      setEvents((prev) => [
        ...prev,
        { agent: "system", type: "error", content: "Connection failed. Is the backend running?" },
      ]);
    } finally {
      setIsStreaming(false);
    }
  }, []);

  return { events, isStreaming, sendMessage };
}
