"use client";
import { useSession, signOut } from "next-auth/react";
import { SignOutIcon } from "./icons";

export default function UserMenu() {
  const { data: session } = useSession();
  const login = (session as any)?.github_login as string | undefined;

  if (!session) return null;

  return (
    <div className="flex items-center justify-between gap-2 px-1">
      <span className="text-xs text-ink-soft truncate tracking-wide">
        {login ? `Signed in as ${login}` : "Signed in"}
      </span>
      <button
        type="button"
        onClick={() => signOut({ callbackUrl: "/" })}
        className="flex items-center gap-1 text-xs font-medium text-ink-soft hover:text-carmine transition-colors flex-shrink-0"
      >
        <SignOutIcon className="w-3.5 h-3.5" />
        Sign out
      </button>
    </div>
  );
}
