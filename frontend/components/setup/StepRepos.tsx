import { useState } from "react";
import { GithubRepo } from "./types";

type Props = {
  repos: GithubRepo[];
  githubUser: string;
  selected: GithubRepo[];
  onSelectionChange: (repos: GithubRepo[]) => void;
  onNext: () => void;
  onBack: () => void;
};

export default function StepRepos({ repos, githubUser, selected, onSelectionChange, onNext, onBack }: Props) {
  const [search, setSearch] = useState("");

  const filtered = repos.filter((r) =>
    r.full_name.toLowerCase().includes(search.toLowerCase()) ||
    r.description.toLowerCase().includes(search.toLowerCase())
  );

  const toggle = (repo: GithubRepo) => {
    const isSelected = selected.some((r) => r.full_name === repo.full_name);
    if (isSelected) {
      onSelectionChange(selected.filter((r) => r.full_name !== repo.full_name));
    } else {
      onSelectionChange([...selected, repo]);
    }
  };

  const isSelected = (repo: GithubRepo) =>
    selected.some((r) => r.full_name === repo.full_name);

  return (
    <div>
      <h2 className="font-display text-lg text-ink mb-1">Select Stock</h2>
      <p className="text-sm text-ink-soft mb-4">
        Signed in as <span className="font-medium text-ink">{githubUser}</span>.
        Pick the repos you want to track as projects.
      </p>

      <input
        type="text"
        placeholder="Filter repositories..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full border border-brass/40 bg-ground rounded-sm px-3 py-2 text-sm text-ink placeholder-ink-soft/50 focus:outline-none focus-visible:border-amber-deep mb-3"
      />

      <div className="border border-brass/30 rounded-sm overflow-y-auto max-h-72 divide-y divide-brass/15 mb-4">
        {filtered.length === 0 && (
          <div className="py-8 text-center text-sm text-ink-soft">No repositories found</div>
        )}
        {filtered.map((repo) => {
          const checked = isSelected(repo);
          return (
            <label
              key={repo.full_name}
              className={`flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-ground transition-colors ${checked ? "bg-amber-glow/15" : "bg-surface"}`}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggle(repo)}
                className="mt-0.5 accent-amber-deep"
              />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-ink truncate">{repo.full_name}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded-sm ${repo.private ? "bg-dust-bg text-dust" : "bg-moss-bg text-moss"}`}>
                    {repo.private ? "private" : "public"}
                  </span>
                </div>
                {repo.description && (
                  <p className="text-xs text-ink-soft mt-0.5 truncate">{repo.description}</p>
                )}
                <p className="text-xs text-ink-soft/60 mt-0.5">updated {repo.updated_at}</p>
              </div>
            </label>
          );
        })}
      </div>

      <p className="text-xs text-ink-soft mb-4">
        {selected.length === 0 ? "No repos selected" : `${selected.length} repo${selected.length > 1 ? "s" : ""} selected`}
      </p>

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="px-4 py-2.5 border border-brass/40 text-ink-soft rounded-sm text-sm hover:bg-ground transition-colors"
        >
          Back
        </button>
        <button
          disabled={selected.length === 0}
          onClick={onNext}
          className="flex-1 py-2.5 bg-amber text-surface rounded-sm text-sm font-medium hover:bg-amber-deep disabled:opacity-40 transition-colors"
        >
          Next — Label projects
        </button>
      </div>
    </div>
  );
}
