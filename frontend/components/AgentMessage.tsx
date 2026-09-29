import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import {
  ScaleIcon,
  BeakerIcon,
  BranchIcon,
  ShelfIcon,
  LabelIcon,
  AlertIcon,
} from "./icons";

type Props = {
  agent: string;
  type: string;
  content: string;
};

const AGENT_STYLES: Record<
  string,
  { label: string; color: string; bg: string; Icon: typeof ScaleIcon }
> = {
  planner: { label: "Planner", color: "text-brass-dark", bg: "bg-surface border-brass/30", Icon: ScaleIcon },
  pm: { label: "PM Agent", color: "text-moss", bg: "bg-moss-bg border-moss/30", Icon: BeakerIcon },
  github: { label: "GitHub", color: "text-ink-soft", bg: "bg-surface border-brass/30", Icon: BranchIcon },
  mcp: { label: "MCP", color: "text-brass-dark", bg: "bg-surface-recessed border-brass/30", Icon: ShelfIcon },
  response: { label: "Response", color: "text-amber-deep", bg: "bg-surface border-amber/40", Icon: LabelIcon },
  system: { label: "System", color: "text-carmine", bg: "bg-carmine-bg border-carmine/30", Icon: AlertIcon },
};

export default function AgentMessage({ agent, type, content }: Props) {
  const style = AGENT_STYLES[agent] ?? {
    label: agent,
    Icon: BeakerIcon,
    color: "text-ink-soft",
    bg: "bg-surface border-brass/30",
  };
  const Icon = style.Icon;

  const isThinking = type === "thinking";
  const isEvent = type === "event";
  const isFinal = type === "final";

  if (isEvent) {
    return (
      <div
        style={{ animation: "settle 0.25s ease-out" }}
        className="flex items-center gap-2 text-xs text-ink-soft py-1 px-2"
      >
        <span className={clsx("font-medium flex items-center gap-1", style.color)}>
          <Icon className="w-3.5 h-3.5" />
          {style.label}
        </span>
        <span className="text-brass/60">·</span>
        <span>{content}</span>
      </div>
    );
  }

  return (
    <div
      style={{
        animation: isFinal
          ? "pour 0.45s cubic-bezier(0.16, 1, 0.3, 1)"
          : "settle 0.25s ease-out",
        transformOrigin: "top",
      }}
      className={clsx("rounded-sm border p-3 mb-2 text-sm", style.bg)}
    >
      <div className={clsx("font-semibold text-xs mb-2 flex items-center gap-1.5", style.color)}>
        <Icon className="w-4 h-4" />
        <span>{style.label}</span>
        {isThinking && <span className="animate-pulse tracking-widest ml-1">···</span>}
      </div>

      {isFinal ? (
        <div className="prose prose-sm max-w-none text-ink prose-headings:font-display prose-headings:text-ink prose-strong:text-ink prose-code:text-amber-deep prose-code:bg-amber-glow/15 prose-code:px-1 prose-code:rounded-sm prose-li:text-ink prose-a:text-amber-deep">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      ) : !isThinking ? (
        <div className="text-ink-soft text-xs leading-relaxed whitespace-pre-wrap">{content}</div>
      ) : null}
    </div>
  );
}
