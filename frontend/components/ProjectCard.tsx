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

export default function ProjectCard({ project, milestones }: Props) {
  const upcoming = milestones
    .filter((m) => !m.completed)
    .sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime())
    .slice(0, 3);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3 mb-2 shadow-sm">
      <div className="font-semibold text-sm text-gray-800">{project.name}</div>
      <div className="text-xs text-gray-400 mb-2">{project.client}</div>
      <div className="space-y-1">
        {upcoming.map((m) => {
          const days = daysUntil(m.due_date);
          const urgent = days <= 3;
          const overdue = days < 0;
          return (
            <div
              key={m.id}
              className={`text-xs flex justify-between items-center ${
                overdue
                  ? "text-red-700 font-bold"
                  : urgent
                  ? "text-orange-600 font-medium"
                  : "text-gray-500"
              }`}
            >
              <span className="truncate mr-2">{m.title}</span>
              <span className="shrink-0">
                {overdue ? `${Math.abs(days)}d overdue` : `${days}d`}
              </span>
            </div>
          );
        })}
        {upcoming.length === 0 && (
          <div className="text-xs text-gray-300">No upcoming milestones</div>
        )}
      </div>
    </div>
  );
}
