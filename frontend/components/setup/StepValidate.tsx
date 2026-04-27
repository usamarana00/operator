type KeyStatus = {
  openai: boolean;
  github: boolean;
  tavily: boolean;
};

type Props = {
  status: KeyStatus | null;
  error: string | null;
  onNext: () => void;
};

function KeyRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <span className={`text-sm font-mono px-2 py-0.5 rounded ${ok ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
        {ok ? "✓" : "✗"}
      </span>
      <span className="text-sm text-gray-700">{label}</span>
      {!ok && <span className="text-xs text-red-500 ml-auto">missing in .env</span>}
      {ok && <span className="text-xs text-green-600 ml-auto">found</span>}
    </div>
  );
}

export default function StepValidate({ status, error, onNext }: Props) {
  const allRequired = status?.openai && status?.github;

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-1">Check API Keys</h2>
      <p className="text-sm text-gray-500 mb-6">
        These keys must be set in <code className="bg-gray-100 px-1 rounded text-xs">backend/.env</code> before continuing.
        They are read server-side and never sent to the browser.
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {status ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 divide-y divide-gray-100 mb-6">
          <KeyRow label="OPENAI_API_KEY" ok={status.openai} />
          <KeyRow label="GITHUB_TOKEN" ok={status.github} />
          <KeyRow label="TAVILY_API_KEY (optional)" ok={status.tavily} />
        </div>
      ) : (
        <div className="h-28 bg-gray-50 rounded-lg flex items-center justify-center text-sm text-gray-400 mb-6">
          Checking...
        </div>
      )}

      {!allRequired && status && (
        <p className="text-xs text-red-600 mb-4">
          Set the missing keys in <code>backend/.env</code>, then restart the backend and refresh this page.
        </p>
      )}

      <button
        disabled={!allRequired}
        onClick={onNext}
        className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
      >
        Next — Select repositories
      </button>
    </div>
  );
}
