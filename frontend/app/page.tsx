"use client";
import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import SetupWizard from "@/components/setup/SetupWizard";
import SignIn from "@/components/SignIn";
import { AgentEvent, useSSE } from "@/lib/useSSE";
import { useBackendToken } from "@/lib/useBackendToken";
import { JarMark } from "@/components/icons";

type AppState = "loading" | "signin" | "setup" | "ready";

export default function Home() {
  const { data: session, status } = useSession();
  const { getToken } = useBackendToken();
  const [appState, setAppState] = useState<AppState>("loading");
  const [proposalSessionId, setProposalSessionId] = useState("");
  const { turns, isStreaming, sendMessage, addTurn, replaceTurnEvents } = useSSE();
  const briefingTurnIdRef = useRef("");
  const proposalTurnIdRef = useRef("");

  useEffect(() => {
    if (status === "loading") return;

    if (!session) {
      setAppState("signin");
      return;
    }

    getToken().then((token) => {
      fetch("/api/backend/setup/status", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
        .then((r) => r.json())
        .then((data) => setAppState(data.configured ? "ready" : "setup"))
        .catch(() => setAppState("setup"));
    });
  }, [session, status, getToken]);

  if (appState === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-ground">
        <div className="text-center text-ink-soft">
          <JarMark className="w-6 h-7 mx-auto mb-3 text-brass/60 animate-pulse" />
          <p className="text-sm font-display">Opening the shop…</p>
        </div>
      </div>
    );
  }

  if (appState === "signin") {
    return <SignIn />;
  }

  if (appState === "setup") {
    return <SetupWizard onComplete={() => setAppState("ready")} />;
  }

  const parseRawSSE = (raw: string): AgentEvent[] => {
    return raw
      .split("\n\n")
      .filter((line) => line.startsWith("data: "))
      .flatMap((line) => {
        try {
          const event = JSON.parse(line.slice(6)) as AgentEvent;
          return event.type === "done" ? [] : [event];
        } catch {
          return [];
        }
      });
  };

  const injectSSEStream = (source: "briefing" | "proposal", raw: string) => {
    const turnIdRef = source === "briefing" ? briefingTurnIdRef : proposalTurnIdRef;

    if (!raw || !turnIdRef.current) {
      turnIdRef.current = addTurn(
        source === "briefing" ? "Morning Briefing" : "New Proposal",
        source,
      );
    }

    if (raw) {
      replaceTurnEvents(turnIdRef.current, parseRawSSE(raw));
    }
  };

  return (
    <main className="flex flex-col md:flex-row h-screen overflow-hidden bg-ground">
      <Sidebar
        onBriefingStream={(raw) => injectSSEStream("briefing", raw)}
        onProposalStream={(raw) => injectSSEStream("proposal", raw)}
        onProposalSessionId={setProposalSessionId}
      />
      <ChatWindow
        turns={turns}
        isStreaming={isStreaming}
        sendMessage={sendMessage}
        proposalSessionId={proposalSessionId}
      />
    </main>
  );
}
