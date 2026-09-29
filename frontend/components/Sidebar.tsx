"use client";
import { useEffect, useState } from "react";
import { useBackendToken } from "@/lib/useBackendToken";
import BriefingButton from "./BriefingButton";
import ProjectCard from "./ProjectCard";
import ProposalWizard from "./ProposalWizard";
import UserMenu from "./UserMenu";
import { LabelIcon, BranchIcon } from "./icons";

type Milestone = {
  id: string;
  title: string;
  due_date: string;
  status: string;
  completed: number;
  project_id: string;
};

type Project = {
  id: string;
  name: string;
  client: string;
  status: string;
  repo_owner?: string | null;
  repo_name?: string | null;
};

type SidebarTab = "projects" | "repos" | "proposals";

const TABS: [SidebarTab, string][] = [
  ["projects", "Shelf"],
  ["repos", "Repos"],
  ["proposals", "Counter"],
];

interface SidebarProps {
  onBriefingStream?: (raw: string) => void;
  onProposalStream?: (raw: string) => void;
  onProposalSessionId?: (id: string) => void;
}

export default function Sidebar({
  onBriefingStream,
  onProposalStream,
  onProposalSessionId,
}: SidebarProps) {
  const { getToken } = useBackendToken();

  const [projects, setProjects] = useState<Project[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [error, setError] = useState(false);
  const [proposalOpen, setProposalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<SidebarTab>("projects");

  useEffect(() => {
    let cancelled = false;
    getToken().then((token) => {
      if (!token || cancelled) return;
      fetch("/api/backend/projects", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => r.json())
        .then((data) => {
          if (cancelled) return;
          setProjects(data.projects ?? []);
          setMilestones(data.milestones ?? []);
        })
        .catch(() => {
          if (!cancelled) setError(true);
        });
    });
    return () => {
      cancelled = true;
    };
  }, [getToken]);

  const linkedProjects = projects.filter((p) => p.repo_owner && p.repo_name);

  return (
    <aside className="w-full md:w-72 max-h-44 md:max-h-none md:min-h-screen bg-surface border-b md:border-b-0 md:border-r border-brass/30 flex-shrink-0 overflow-y-auto flex flex-col">
      <div className="p-4 pb-3">
        <UserMenu />
      </div>

      <div className="px-4 border-b border-brass/30">
        <div className="flex gap-4">
          {TABS.map(([tab, label]) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`relative pb-2.5 text-sm font-display transition-colors ${
                activeTab === tab ? "text-ink" : "text-ink-soft hover:text-ink"
              }`}
            >
              {label}
              {activeTab === tab && (
                <span className="absolute left-0 right-0 -bottom-px h-0.5 bg-amber-deep rounded-full" />
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 p-4 overflow-y-auto">
        {error && (
          <p className="text-xs text-carmine bg-carmine-bg rounded-sm px-2 py-1.5 mb-3">
            The counter is unreachable — backend offline.
          </p>
        )}

        {activeTab === "projects" && (
          <div>
            {projects.map((p) => (
              <ProjectCard
                key={p.id}
                project={p}
                milestones={milestones.filter((m) => m.project_id === p.id)}
              />
            ))}
            {!error && projects.length === 0 && (
              <p className="text-xs text-ink-soft">The shelf is bare — reading stock…</p>
            )}
          </div>
        )}

        {activeTab === "repos" && (
          <div className="space-y-2">
            {linkedProjects.map((project) => (
              <a
                key={project.id}
                href={`https://github.com/${project.repo_owner}/${project.repo_name}`}
                target="_blank"
                rel="noreferrer"
                className="flex gap-2.5 rounded-sm border border-brass/40 bg-ground px-3 py-3 hover:border-brass hover:bg-surface-recessed/60 transition-colors"
              >
                <BranchIcon className="w-4 h-4 mt-0.5 flex-shrink-0 text-brass-dark" />
                <div className="min-w-0">
                  <div className="text-sm font-medium text-ink truncate">
                    {project.repo_name}
                  </div>
                  <div className="text-xs text-ink-soft truncate">
                    {project.repo_owner}/{project.repo_name}
                  </div>
                  <div className="mt-1.5 text-xs text-dust truncate">{project.name}</div>
                </div>
              </a>
            ))}
            {!error && linkedProjects.length === 0 && (
              <p className="text-xs text-ink-soft">No repositories linked to the shelf yet.</p>
            )}
          </div>
        )}

        {activeTab === "proposals" && (
          <div className="space-y-1">
            <BriefingButton onStream={onBriefingStream ?? (() => {})} />
            <button
              onClick={() => setProposalOpen(true)}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-sm text-sm font-medium transition-colors text-ink-soft hover:text-ink hover:bg-ground"
            >
              <LabelIcon className="w-4 h-4 flex-shrink-0" />
              <span>New Proposal</span>
            </button>
          </div>
        )}
      </div>

      <ProposalWizard
        open={proposalOpen}
        onClose={() => setProposalOpen(false)}
        onStream={onProposalStream ?? (() => {})}
        onSessionId={(id) => {
          onProposalSessionId?.(id);
        }}
      />
    </aside>
  );
}
