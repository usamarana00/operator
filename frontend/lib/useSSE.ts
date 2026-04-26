"use client";
import { useState, useCallback } from "react";

export type AgentEvent = {
  agent: string;
  type: string;
  content: string;
};

export type Turn = {
  userMessage: string;
  events: AgentEvent[];
};

export function useSSE() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(async (message: string, sessionId: string) => {
    const turnIndex = turns.length;
    setTurns((prev) => [...prev, { userMessage: message, events: [] }]);
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
                setTurns((prev) => {
                  const updated = [...prev];
                  updated[turnIndex] = {
                    ...updated[turnIndex],
                    events: [...updated[turnIndex].events, event],
                  };
                  return updated;
                });
              }
            } catch {
              // skip malformed events
            }
          }
        }
      }
    } catch {
      setTurns((prev) => {
        const updated = [...prev];
        updated[turnIndex] = {
          ...updated[turnIndex],
          events: [
            ...updated[turnIndex].events,
            { agent: "system", type: "error", content: "Connection failed. Is the backend running?" },
          ],
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  }, [turns.length]);

  return { turns, isStreaming, sendMessage };
}
