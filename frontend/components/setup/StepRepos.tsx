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
      <h2 className="text-lg font-semibold text-gray-800 mb-1">Select Repositories</h2>
      <p className="text-sm text-gray-500 mb-4">
        Signed in as <span className="font-medium text-gray-700">{githubUser}</span>.
        Pick the repos you want to track as projects.
      </p>

      <input
        type="text"
        placeholder="Filter repositories..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-3"
      />

      <div className="border border-gray-200 rounded-lg overflow-y-auto max-h-72 divide-y divide-gray-100 mb-4">
        {filtered.length === 0 && (
          <div className="py-8 text-center text-sm text-gray-400">No repositories found</div>
        )}
        {filtered.map((repo) => {
          const checked = isSelected(repo);
          return (
            <label
              key={repo.full_name}
              className={`flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors ${checked ? "bg-blue-50" : ""}`}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggle(repo)}
                className="mt-0.5 accent-blue-600"
              />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-800 truncate">{repo.full_name}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${repo.private ? "bg-gray-100 text-gray-500" : "bg-green-50 text-green-600"}`}>
                    {repo.private ? "private" : "public"}
                  </span>
                </div>
                {repo.description && (
                  <p className="text-xs text-gray-400 mt-0.5 truncate">{repo.description}</p>
                )}
                <p className="text-xs text-gray-300 mt-0.5">updated {repo.updated_at}</p>
              </div>
            </label>
          );
        })}
      </div>

      <p className="text-xs text-gray-400 mb-4">
        {selected.length === 0 ? "No repos selected" : `${selected.length} repo${selected.length > 1 ? "s" : ""} selected`}
      </p>

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        <button
          disabled={selected.length === 0}
          onClick={onNext}
          className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
        >
          Next — Configure projects
        </button>
      </div>
    </div>
  );
}
