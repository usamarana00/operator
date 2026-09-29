"use client";
import { useCallback, useRef } from "react";
import { useSession } from "next-auth/react";

const REFRESH_MARGIN_MS = 30_000;

export function useBackendToken() {
  const { data: session, status } = useSession();
  const cacheRef = useRef<{ token: string; expiresAt: number } | null>(null);

  const getToken = useCallback(async (): Promise<string | undefined> => {
    if (status !== "authenticated" || !session) return undefined;

    const cached = cacheRef.current;
    if (cached && cached.expiresAt - REFRESH_MARGIN_MS > Date.now()) {
      return cached.token;
    }

    const res = await fetch("/api/backend-token");
    if (!res.ok) return undefined;

    const data = await res.json();
    cacheRef.current = {
      token: data.token as string,
      expiresAt: Date.now() + (data.expiresIn as number) * 1000,
    };
    return cacheRef.current.token;
  }, [session, status]);

  return { getToken };
}
