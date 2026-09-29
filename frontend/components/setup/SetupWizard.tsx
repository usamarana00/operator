"use client";
import { useEffect, useState } from "react";
import { useBackendToken } from "@/lib/useBackendToken";
import StepValidate from "./StepValidate";
import StepRepos from "./StepRepos";
import StepConfigure from "./StepConfigure";
import StepBuilding from "./StepBuilding";
import { GithubRepo, ProjectConfig } from "./types";
import UserMenu from "@/components/UserMenu";
import { JarMark, CheckIcon } from "@/components/icons";

type Props = {
  onComplete: () => void;
};

const STEPS = ["Unlock", "Select", "Label", "Compound"];
const BACKEND = "/api/backend";

export default function SetupWizard({ onComplete }: Props) {
  const { getToken } = useBackendToken();
  const [token, setToken] = useState("");

  useEffect(() => {
    let cancelled = false;
    getToken().then((t) => {
      if (!cancelled) setToken(t ?? "");
    });
    return () => {
      cancelled = true;
    };
  }, [getToken]);

  const [step, setStep] = useState(0);

  // Step 1 state
  const [repos, setRepos] = useState<GithubRepo[]>([]);
  const [githubUser, setGithubUser] = useState("");
  const [selectedRepos, setSelectedRepos] = useState<GithubRepo[]>([]);
  const [repoLoading, setRepoLoading] = useState(false);
  const [repoError, setRepoError] = useState<string | null>(null);

  // Step 2 state
  const [projects, setProjects] = useState<ProjectConfig[]>([]);

  const authHeaders = {
    Authorization: `Bearer ${token}`,
  };

  const goToRepos = async () => {
    console.info("[setup] repos step requested", {
      hasToken: Boolean(token),
      cachedRepoCount: repos.length,
    });
    setStep(1);
    if (repos.length > 0) {
      console.info("[setup] using cached repos", { repoCount: repos.length });
      return;
    }
    setRepoLoading(true);
    setRepoError(null);
    try {
      const r = await fetch(`${BACKEND}/setup/repos`, { headers: authHeaders });
      const data = await r.json();
      console.info("[setup] repos response", {
        ok: r.ok,
        status: r.status,
        hasError: Boolean(data.error),
        repoCount: Array.isArray(data.repos) ? data.repos.length : 0,
      });
      if (!r.ok) {
        throw new Error(data.detail ?? data.error ?? `Failed to fetch repositories (${r.status})`);
      }
      if (data.error) {
        setRepoError(data.error);
        setStep(0);
      } else {
        setRepos(data.repos);
        setGithubUser(data.user?.login ?? "");
      }
    } catch (err: any) {
      console.error("[setup] repos request failed", {
        message: err?.message ?? "Unknown error",
      });
      setRepoError(err?.message ?? "Failed to fetch repositories.");
      setStep(0);
    } finally {
      setRepoLoading(false);
    }
  };

  const goToConfigure = () => {
    setProjects(
      selectedRepos.map((repo) => ({
        repo,
        name: repo.full_name
          .split("/")[1]
          .replace(/-/g, " ")
          .replace(/\b\w/g, (c) => c.toUpperCase()),
        client: "",
        milestones: [],
      }))
    );
    setStep(2);
  };

  return (
    <div className="min-h-screen bg-ground flex items-center justify-center p-4">
      <div className="w-full max-w-xl">
        <div className="flex justify-end mb-2">
          <UserMenu />
        </div>
        <div className="text-center mb-8">
          <JarMark className="w-8 h-10 mx-auto mb-3 text-amber" />
          <h1 className="font-display text-2xl text-ink">Stocking the Shelf</h1>
          <p className="text-sm text-ink-soft mt-1">Configure your projects once — then just chat.</p>
        </div>

        <div className="flex items-center justify-center flex-wrap gap-x-2 gap-y-2 mb-6">
          {STEPS.map((label, i) => (
            <div key={i} className="flex items-center gap-2">
              <div
                className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold border transition-all ${
                  i < step
                    ? "bg-amber border-amber text-surface"
                    : i === step
                    ? "border-amber-deep text-amber-deep bg-surface"
                    : "border-brass/30 text-ink-soft/50 bg-surface"
                }`}
              >
                {i < step ? <CheckIcon className="w-3.5 h-3.5" /> : i + 1}
              </div>
              <span
                className={`text-xs font-display ${
                  i === step ? "text-ink" : "text-ink-soft/60"
                }`}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div className={`w-6 h-px ${i < step ? "bg-amber/50" : "bg-brass/25"}`} />
              )}
            </div>
          ))}
        </div>

        <div className="bg-surface border border-brass/40 rounded-sm p-6">
          {step === 0 && <StepValidate token={token} onNext={goToRepos} />}

          {step === 1 &&
            (repoLoading ? (
              <div className="py-16 text-center text-sm text-ink-soft">
                <JarMark className="w-6 h-7 mx-auto mb-3 text-brass/60 animate-pulse" />
                Reading the shelf — fetching your GitHub repositories...
              </div>
            ) : (
              <StepRepos
                repos={repos}
                githubUser={githubUser}
                selected={selectedRepos}
                onSelectionChange={setSelectedRepos}
                onNext={goToConfigure}
                onBack={() => setStep(0)}
              />
            ))}

          {step === 2 && (
            <StepConfigure
              projects={projects}
              onChange={setProjects}
              onNext={() => setStep(3)}
              onBack={() => setStep(1)}
            />
          )}

          {step === 3 && <StepBuilding projects={projects} token={token} onComplete={onComplete} />}
        </div>

        <p className="text-center text-xs text-ink-soft/70 mt-4">
          Signed in via GitHub OAuth. Your OpenAI key is encrypted at rest.
        </p>
      </div>
    </div>
  );
}
