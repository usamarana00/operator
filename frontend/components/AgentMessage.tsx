import clsx from "clsx";

type Props = {
  agent: string;
  type: string;
  content: string;
};

const AGENT_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  planner:  { label: "Planner",   color: "text-purple-700", bg: "bg-purple-50 border-purple-200" },
  pm:       { label: "PM Agent",  color: "text-blue-700",   bg: "bg-blue-50 border-blue-200" },
  github:   { label: "GitHub",    color: "text-gray-700",   bg: "bg-gray-50 border-gray-200" },
  response: { label: "Response",  color: "text-green-700",  bg: "bg-green-50 border-green-200" },
  system:   { label: "System",    color: "text-red-700",    bg: "bg-red-50 border-red-200" },
};

export default function AgentMessage({ agent, type, content }: Props) {
  const style = AGENT_STYLES[agent] ?? {
    label: agent,
    color: "text-slate-700",
    bg: "bg-slate-50 border-slate-200",
  };
  const isThinking = type === "thinking";

  return (
    <div className={clsx("rounded-lg border p-3 mb-2 text-sm", style.bg)}>
      <div className={clsx("font-semibold text-xs mb-1 flex items-center gap-1", style.color)}>
        {style.label}
        {isThinking && (
          <span className="animate-pulse tracking-widest">···</span>
        )}
      </div>
      {!isThinking && (
        <div className="text-gray-800 whitespace-pre-wrap leading-relaxed">{content}</div>
      )}
    </div>
  );
}
