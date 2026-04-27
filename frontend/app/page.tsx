"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import SetupWizard from "@/components/setup/SetupWizard";

type AppState = "loading" | "setup" | "ready";

export default function Home() {
  const [appState, setAppState] = useState<AppState>("loading");

  useEffect(() => {
    fetch("/api/backend/setup/status")
      .then((r) => r.json())
      .then((data) => setAppState(data.configured ? "ready" : "setup"))
      .catch(() => setAppState("setup")); // if backend is down, show setup
  }, []);

  if (appState === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-center text-gray-400">
          <div className="text-3xl mb-3 animate-pulse">🤖</div>
          <p className="text-sm">Starting...</p>
        </div>
      </div>
    );
  }

  if (appState === "setup") {
    return <SetupWizard onComplete={() => setAppState("ready")} />;
  }

  return (
    <main className="flex h-screen overflow-hidden bg-white">
      <Sidebar />
      <ChatWindow />
    </main>
  );
}
