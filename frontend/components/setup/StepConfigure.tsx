import { ProjectConfig, Milestone } from "./types";

type Props = {
  projects: ProjectConfig[];
  onChange: (projects: ProjectConfig[]) => void;
  onNext: () => void;
  onBack: () => void;
};

function MilestoneRow({
  milestone,
  onUpdate,
  onRemove,
}: {
  milestone: Milestone;
  onUpdate: (m: Milestone) => void;
  onRemove: () => void;
}) {
  return (
    <div className="flex gap-2 items-center">
      <input
        type="text"
        placeholder="Milestone title"
        value={milestone.title}
        onChange={(e) => onUpdate({ ...milestone, title: e.target.value })}
        className="flex-1 border border-gray-200 rounded px-2 py-1.5 text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <input
        type="date"
        value={milestone.due_date}
        onChange={(e) => onUpdate({ ...milestone, due_date: e.target.value })}
        className="border border-gray-200 rounded px-2 py-1.5 text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <button
        onClick={onRemove}
        className="text-gray-300 hover:text-red-400 text-sm px-1 transition-colors"
        title="Remove milestone"
      >
        ✕
      </button>
    </div>
  );
}

function ProjectForm({
  project,
  index,
  onChange,
}: {
  project: ProjectConfig;
  index: number;
  onChange: (p: ProjectConfig) => void;
}) {
  const addMilestone = () =>
    onChange({
      ...project,
      milestones: [...project.milestones, { title: "", due_date: "" }],
    });

  const updateMilestone = (i: number, m: Milestone) =>
    onChange({
      ...project,
      milestones: project.milestones.map((x, j) => (j === i ? m : x)),
    });

  const removeMilestone = (i: number) =>
    onChange({
      ...project,
      milestones: project.milestones.filter((_, j) => j !== i),
    });

  return (
    <div className="border border-gray-200 rounded-lg p-4 mb-3">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-mono">
          {project.repo.full_name}
        </span>
        <span className={`text-xs px-1.5 py-0.5 rounded ${project.repo.private ? "bg-gray-100 text-gray-500" : "bg-green-50 text-green-600"}`}>
          {project.repo.private ? "private" : "public"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Project name</label>
          <input
            type="text"
            value={project.name}
            onChange={(e) => onChange({ ...project, name: e.target.value })}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Client / company</label>
          <input
            type="text"
            value={project.client}
            onChange={(e) => onChange({ ...project, client: e.target.value })}
            placeholder="e.g. Acme Corp"
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs text-gray-500">Milestones (optional)</label>
          <button
            onClick={addMilestone}
            className="text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            + Add milestone
          </button>
        </div>
        <div className="space-y-2">
          {project.milestones.map((m, i) => (
            <MilestoneRow
              key={i}
              milestone={m}
              onUpdate={(updated) => updateMilestone(i, updated)}
              onRemove={() => removeMilestone(i)}
            />
          ))}
          {project.milestones.length === 0 && (
            <p className="text-xs text-gray-300 italic">No milestones added</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function StepConfigure({ projects, onChange, onNext, onBack }: Props) {
  const updateProject = (i: number, p: ProjectConfig) =>
    onChange(projects.map((x, j) => (j === i ? p : x)));

  const allValid = projects.every((p) => p.name.trim() && p.client.trim());

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-1">Configure Projects</h2>
      <p className="text-sm text-gray-500 mb-4">
        Give each repo a project name and client. Add milestones if you have deadlines to track.
      </p>

      <div className="overflow-y-auto max-h-80">
        {projects.map((p, i) => (
          <ProjectForm key={p.repo.full_name} project={p} index={i} onChange={(updated) => updateProject(i, updated)} />
        ))}
      </div>

      <div className="flex gap-3 mt-4">
        <button
          onClick={onBack}
          className="px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        <button
          disabled={!allValid}
          onClick={onNext}
          className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
        >
          Build knowledge base
        </button>
      </div>
    </div>
  );
}
