"use client";
import { useState, useCallback } from "react";
import { useSession } from "next-auth/react";

export type AgentEvent = {
  agent: string;
  type: string;
  content: string;
};

export type Turn = {
  id: string;
  userMessage: string;
  events: AgentEvent[];
  source?: "chat" | "briefing" | "proposal";
};

export function useSSE() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken as string | undefined;

  const [turns, setTurns] = useState<Turn[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const addTurn = useCallback((userMessage: string, source: Turn["source"] = "chat") => {
    const id = crypto.randomUUID();
    setTurns((prev) => [...prev, { id, userMessage, events: [], source }]);
    return id;
  }, []);

  const replaceTurnEvents = useCallback((turnId: string, events: AgentEvent[]) => {
    setTurns((prev) =>
      prev.map((turn) => (turn.id === turnId ? { ...turn, events } : turn)),
    );
  }, []);

  const sendMessage = useCallback(async (message: string, sessionId: string) => {
    const turnIndex = turns.length;
    const turnId = crypto.randomUUID();
    setTurns((prev) => [...prev, { id: turnId, userMessage: message, events: [], source: "chat" }]);
    setIsStreaming(true);

    try {
      const response = await fetch("/api/backend/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
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
                  const currentTurn = updated[turnIndex];
                  if (!currentTurn || currentTurn.id !== turnId) return prev;
                  updated[turnIndex] = {
                    ...currentTurn,
                    events: [...currentTurn.events, event],
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
        const currentTurn = updated[turnIndex];
        if (!currentTurn || currentTurn.id !== turnId) return prev;
        updated[turnIndex] = {
          ...currentTurn,
          events: [
            ...currentTurn.events,
            { agent: "system", type: "error", content: "Connection failed. Is the backend running?" },
          ],
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  }, [turns.length, token]);

  return { turns, isStreaming, sendMessage, addTurn, replaceTurnEvents };
}
