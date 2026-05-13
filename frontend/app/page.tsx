"use client";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import SetupWizard from "@/components/setup/SetupWizard";
import SignIn from "@/components/SignIn";

type AppState = "loading" | "signin" | "setup" | "ready";

export default function Home() {
  const { data: session, status } = useSession();
  const [appState, setAppState] = useState<AppState>("loading");

  useEffect(() => {
    if (status === "loading") return;

    if (!session) {
      setAppState("signin");
      return;
    }

    const token = (session as any).accessToken as string | undefined;

    fetch("/api/backend/setup/status", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then((data) => setAppState(data.configured ? "ready" : "setup"))
      .catch(() => setAppState("setup"));
  }, [session, status]);

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

  if (appState === "signin") {
    return <SignIn />;
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
