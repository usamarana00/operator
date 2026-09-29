"use client";
import { signIn } from "next-auth/react";
import { JarMark, GithubMark } from "./icons";

export default function SignIn() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-ground px-4">
      <div className="max-w-sm w-full">
        <div className="relative border border-brass/60 rounded-sm bg-surface p-10 text-center shadow-[0_1px_0_var(--surface)_inset,0_18px_36px_-24px_rgba(43,36,32,0.45)]">
          <span className="pointer-events-none absolute inset-2 rounded-[2px] border border-brass/25" />

          <JarMark className="w-9 h-11 mx-auto mb-5 text-amber" />

          <h1 className="font-display text-3xl text-ink tracking-tight">Keystone</h1>
          <p className="font-display italic text-sm text-ink-soft mt-2 mb-8 leading-relaxed">
            A dispensary for your freelance practice — deadlines, repos, and
            proposals, compounded from what you're actually working on.
          </p>

          <button
            onClick={() => signIn("github", { callbackUrl: "/" })}
            className="w-full flex items-center justify-center gap-3 bg-ink hover:bg-amber-deep text-surface font-medium py-3 px-6 rounded-sm transition-colors duration-150"
          >
            <GithubMark className="w-5 h-5" />
            Sign in with GitHub
          </button>

          <p className="text-xs text-ink-soft/80 mt-6 tracking-wide">
            Requests <code className="bg-surface-recessed px-1 rounded-sm">repo</code>,{" "}
            <code className="bg-surface-recessed px-1 rounded-sm">read:user</code> to
            stock your shelves.
          </p>
        </div>
      </div>
    </div>
  );
}
