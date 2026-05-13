"use client";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import StepValidate from "./StepValidate";
import StepRepos from "./StepRepos";
import StepConfigure from "./StepConfigure";
import StepBuilding from "./StepBuilding";
import { GithubRepo, ProjectConfig } from "./types";

type Props = {
  onComplete: () => void;
};

const STEPS = ["Keys", "Repos", "Configure", "Build"];
const BACKEND = "/api/backend";

export default function SetupWizard({ onComplete }: Props) {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken as string ?? "";

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
    setStep(1);
    if (repos.length > 0) return;
    setRepoLoading(true);
    setRepoError(null);
    try {
      const r = await fetch(`${BACKEND}/setup/repos`, { headers: authHeaders });
      const data = await r.json();
      if (data.error) {
        setRepoError(data.error);
        setStep(0);
      } else {
        setRepos(data.repos);
        setGithubUser(data.user?.login ?? "");
      }
    } catch {
      setRepoError("Failed to fetch repositories.");
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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center p-4">
      <div className="w-full max-w-xl">
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">🤖</div>
          <h1 className="text-2xl font-bold text-gray-900">Freelance Agent Setup</h1>
          <p className="text-sm text-gray-500 mt-1">Configure your projects once — then just chat.</p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {STEPS.map((label, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold border-2 transition-all ${
                i < step
                  ? "bg-blue-600 border-blue-600 text-white"
                  : i === step
                  ? "border-blue-600 text-blue-600 bg-white"
                  : "border-gray-200 text-gray-300 bg-white"
              }`}>
                {i < step ? "✓" : i + 1}
              </div>
              <span className={`text-xs ${i === step ? "text-blue-600 font-medium" : "text-gray-400"}`}>
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div className={`w-6 h-px ${i < step ? "bg-blue-400" : "bg-gray-200"}`} />
              )}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          {step === 0 && (
            <StepValidate token={token} onNext={goToRepos} />
          )}

          {step === 1 && (
            repoLoading ? (
              <div className="py-16 text-center text-sm text-gray-400">
                <div className="animate-spin text-2xl mb-3">⚙</div>
                Fetching your GitHub repositories...
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
            )
          )}

          {step === 2 && (
            <StepConfigure
              projects={projects}
              onChange={setProjects}
              onNext={() => setStep(3)}
              onBack={() => setStep(1)}
            />
          )}

          {step === 3 && (
            <StepBuilding
              projects={projects}
              token={token}
              onComplete={onComplete}
            />
          )}
        </div>

        <p className="text-center text-xs text-gray-400 mt-4">
          Signed in via GitHub OAuth. Your OpenAI key is encrypted at rest.
        </p>
      </div>
    </div>
  );
}
