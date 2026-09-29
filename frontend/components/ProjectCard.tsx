type Milestone = {
  id: string;
  title: string;
  due_date: string;
  completed: number;
  project_id: string;
};

type Project = {
  id: string;
  name: string;
  client: string;
  status: string;
};

type Props = {
  project: Project;
  milestones: Milestone[];
};

function daysUntil(dateStr: string): number {
  const due = new Date(dateStr);
  const now = new Date();
  return Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

function statusFor(days: number): { word: string; color: string; bg: string } {
  if (days < 0) return { word: "overdue", color: "text-carmine", bg: "bg-carmine-bg" };
  if (days <= 3) return { word: "due soon", color: "text-amber-deep", bg: "bg-amber-glow/25" };
  return { word: "on track", color: "text-moss", bg: "bg-moss-bg" };
}

export default function ProjectCard({ project, milestones }: Props) {
  const upcoming = milestones
    .filter((m) => !m.completed)
    .sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime())
    .slice(0, 3);

  return (
    <div className="relative bg-surface border border-brass/40 rounded-sm px-3.5 py-3 mb-2.5">
      <span
        aria-hidden
        className="absolute -top-1 left-3.5 w-2 h-2 rounded-full bg-brass/70 border border-brass-dark/40"
      />
      <div className="font-display text-base text-ink leading-tight truncate">{project.name}</div>
      <div className="text-xs text-ink-soft mb-2">{project.client || "personal"}</div>

      <div className="space-y-1.5">
        {upcoming.map((m) => {
          const days = daysUntil(m.due_date);
          const status = statusFor(days);
          return (
            <div key={m.id} className="flex items-center justify-between gap-2 text-xs">
              <span className="truncate text-ink-soft">{m.title}</span>
              <span
                className={`shrink-0 tabular px-1.5 py-0.5 rounded-sm font-medium ${status.color} ${status.bg}`}
              >
                {days < 0 ? `${status.word} · ${Math.abs(days)}d` : `${status.word} · ${days}d`}
              </span>
            </div>
          );
        })}
        {upcoming.length === 0 && (
          <div className="text-xs text-dust px-1.5 py-0.5 rounded-sm bg-dust-bg inline-block">
            no upcoming milestones
          </div>
        )}
      </div>
    </div>
  );
}
