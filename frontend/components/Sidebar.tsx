"use client";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import ProjectCard from "./ProjectCard";

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
};

export default function Sidebar() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken as string | undefined;

  const [projects, setProjects] = useState<Project[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [error, setError] = useState(false);

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
    <aside className="w-64 min-h-screen bg-gray-50 border-r border-gray-200 p-4 flex-shrink-0 overflow-y-auto">
      <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
        Active Projects
      </h2>
      {error && (
        <p className="text-xs text-red-400">Backend offline</p>
      )}
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
    </aside>
  );
}
