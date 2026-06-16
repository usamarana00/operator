"use client";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import BriefingButton from "./BriefingButton";
import ProjectCard from "./ProjectCard";
import ProposalWizard from "./ProposalWizard";

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
  const { data: session } = useSession();
  const token = (session as any)?.accessToken as string | undefined;

  const [projects, setProjects] = useState<Project[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [error, setError] = useState(false);
  const [proposalOpen, setProposalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<SidebarTab>("projects");

  useEffect(() => {
    if (!token) return;
    fetch("/api/backend/projects", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        setProjects(data.projects ?? []);
        setMilestones(data.milestones ?? []);
      })
      .catch(() => setError(true));
  }, [token]);

  return (
    <aside className="w-72 min-h-screen bg-gray-50 border-r border-gray-200 p-4 flex-shrink-0 overflow-y-auto">
      <div className="min-h-full flex flex-col">
        <div className="flex-1">
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
            Workspace
          </h2>

          <div className="grid grid-cols-3 gap-1 rounded-lg bg-gray-100 p-1 mb-4">
            {[
              ["projects", "Projects"],
              ["repos", "Repos"],
              ["proposals", "Proposals"],
            ].map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab as SidebarTab)}
                className={`px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  activeTab === tab
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-800"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {error && <p className="text-xs text-red-400">Backend offline</p>}

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
                <p className="text-xs text-gray-300">Loading...</p>
              )}
            </div>
          )}

          {activeTab === "repos" && (
            <div className="space-y-2">
              {projects
                .filter((project) => project.repo_owner && project.repo_name)
                .map((project) => (
                  <a
                    key={project.id}
                    href={`https://github.com/${project.repo_owner}/${project.repo_name}`}
                    target="_blank"
                    rel="noreferrer"
                    className="block rounded-lg border border-gray-200 bg-white px-3 py-3 shadow-sm hover:border-gray-300 hover:shadow transition"
                  >
                    <div className="text-sm font-semibold text-gray-900 truncate">
                      {project.repo_name}
                    </div>
                    <div className="text-xs text-gray-500 truncate">
                      {project.repo_owner}/{project.repo_name}
                    </div>
                    <div className="mt-2 text-xs text-gray-400 truncate">
                      {project.name}
                    </div>
                  </a>
                ))}
              {!error &&
                projects.filter((project) => project.repo_owner && project.repo_name)
                  .length === 0 && (
                  <p className="text-xs text-gray-400">
                    No repositories linked.
                  </p>
                )}
            </div>
          )}

          {activeTab === "proposals" && (
            <div className="space-y-2">
              <BriefingButton onStream={onBriefingStream ?? (() => {})} />
              <button
                onClick={() => setProposalOpen(true)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              >
                <span>Doc</span>
                <span>New Proposal</span>
              </button>
            </div>
          )}
        </div>
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
