import { ProjectConfig, Milestone } from "./types";
import { PlusIcon, TrashIcon } from "@/components/icons";

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
        className="flex-1 border border-brass/30 bg-ground rounded-sm px-2 py-1.5 text-xs text-ink focus:outline-none focus-visible:border-amber-deep"
      />
      <input
        type="date"
        value={milestone.due_date}
        onChange={(e) => onUpdate({ ...milestone, due_date: e.target.value })}
        className="border border-brass/30 bg-ground rounded-sm px-2 py-1.5 text-xs text-ink tabular focus:outline-none focus-visible:border-amber-deep"
      />
      <button
        onClick={onRemove}
        className="text-ink-soft/50 hover:text-carmine p-1 transition-colors"
        title="Remove milestone"
      >
        <TrashIcon className="w-3.5 h-3.5" />
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
    <div className="relative border border-brass/40 bg-surface rounded-sm p-4 mb-3">
      <span
        aria-hidden
        className="absolute -top-1 left-4 w-2 h-2 rounded-full bg-brass/70 border border-brass-dark/40"
      />
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs bg-ground text-ink-soft px-2 py-0.5 rounded-sm font-mono">
          {project.repo.full_name}
        </span>
        <span className={`text-xs px-1.5 py-0.5 rounded-sm ${project.repo.private ? "bg-dust-bg text-dust" : "bg-moss-bg text-moss"}`}>
          {project.repo.private ? "private" : "public"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label className="block text-xs text-ink-soft mb-1">Project name</label>
          <input
            type="text"
            value={project.name}
            onChange={(e) => onChange({ ...project, name: e.target.value })}
            className="w-full border border-brass/40 bg-ground rounded-sm px-3 py-2 text-sm text-ink focus:outline-none focus-visible:border-amber-deep"
          />
        </div>
        <div>
          <label className="block text-xs text-ink-soft mb-1">Client / company</label>
          <input
            type="text"
            value={project.client}
            onChange={(e) => onChange({ ...project, client: e.target.value })}
            placeholder="e.g. Acme Corp"
            className="w-full border border-brass/40 bg-ground rounded-sm px-3 py-2 text-sm text-ink placeholder-ink-soft/50 focus:outline-none focus-visible:border-amber-deep"
          />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs text-ink-soft">Milestones (optional)</label>
          <button
            onClick={addMilestone}
            className="flex items-center gap-1 text-xs text-amber-deep hover:text-amber font-medium"
          >
            <PlusIcon className="w-3 h-3" />
            Add milestone
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
            <p className="text-xs text-ink-soft/60 italic">No milestones added</p>
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
      <h2 className="font-display text-lg text-ink mb-1">Label Each Jar</h2>
      <p className="text-sm text-ink-soft mb-4">
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
          className="px-4 py-2.5 border border-brass/40 text-ink-soft rounded-sm text-sm hover:bg-ground transition-colors"
        >
          Back
        </button>
        <button
          disabled={!allValid}
          onClick={onNext}
          className="flex-1 py-2.5 bg-amber text-surface rounded-sm text-sm font-medium hover:bg-amber-deep disabled:opacity-40 transition-colors"
        >
          Compound the shelf
        </button>
      </div>
    </div>
  );
}
