import clsx from "clsx";
import ReactMarkdown from "react-markdown";

type Props = {
  agent: string;
  type: string;
  content: string;
};

const AGENT_STYLES: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  planner:  { label: "Planner",   color: "text-purple-700", bg: "bg-purple-50 border-purple-200",  icon: "🧠" },
  pm:       { label: "PM Agent",  color: "text-blue-700",   bg: "bg-blue-50 border-blue-200",      icon: "📋" },
  github:   { label: "GitHub",    color: "text-gray-700",   bg: "bg-gray-50 border-gray-200",      icon: "🐙" },
  mcp:      { label: "MCP",       color: "text-orange-700", bg: "bg-orange-50 border-orange-200",  icon: "🔌" },
  response: { label: "Response",  color: "text-green-700",  bg: "bg-green-50 border-green-200",    icon: "✅" },
  system:   { label: "System",    color: "text-red-700",    bg: "bg-red-50 border-red-200",        icon: "⚠️" },
};

export default function AgentMessage({ agent, type, content }: Props) {
  const style = AGENT_STYLES[agent] ?? {
    label: agent,
    icon: "•",
    color: "text-slate-700",
    bg: "bg-slate-50 border-slate-200",
  };

  const isThinking = type === "thinking";
  const isEvent = type === "event";
  const isFinal = type === "final";

  if (isEvent) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-500 py-1 px-2">
        <span className={clsx("font-medium", style.color)}>{style.icon} {style.label}</span>
        <span className="text-gray-400">›</span>
        <span>{content}</span>
      </div>
    );
  }

  return (
    <div className={clsx("rounded-lg border p-3 mb-2 text-sm", style.bg)}>
      <div className={clsx("font-semibold text-xs mb-2 flex items-center gap-1.5", style.color)}>
        <span>{style.icon}</span>
        <span>{style.label}</span>
        {isThinking && <span className="animate-pulse tracking-widest ml-1">···</span>}
      </div>

      {isFinal ? (
        <div className="prose prose-sm max-w-none text-gray-800 prose-headings:text-gray-800 prose-strong:text-gray-900 prose-code:text-blue-700 prose-code:bg-blue-50 prose-code:px-1 prose-code:rounded prose-li:text-gray-800">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      ) : !isThinking ? (
        <div className="text-gray-700 text-xs leading-relaxed whitespace-pre-wrap">{content}</div>
      ) : null}
    </div>
  );
}
