import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Card } from "@/components/ui/primitives";

export function HistorySidebar({
  onPick,
  activeThreadId,
}: {
  onPick: (question: string, threadId?: string) => void;
  activeThreadId?: string;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["history"],
    queryFn: () => api.history(50),
  });

  return (
    <Card className="flex h-full flex-col">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-700">Query History</h2>
        <p className="text-xs text-slate-400">{data?.total ?? 0} question(s)</p>
      </div>
      <div className="scroll-thin flex-1 space-y-1 overflow-auto p-2">
        {isLoading && <p className="px-2 py-4 text-xs text-slate-400">Loading…</p>}
        {!isLoading && data?.items.length === 0 && (
          <p className="px-2 py-4 text-xs text-slate-400">No questions yet.</p>
        )}
        {data?.items.map((h) => (
          <button
            key={h.id}
            onClick={() => onPick(h.question, h.thread_id)}
            className={`block w-full rounded-lg px-3 py-2 text-left text-sm transition hover:bg-slate-100 ${
              h.thread_id === activeThreadId ? "bg-brand-50 text-brand-700" : "text-slate-700"
            }`}
          >
            <span className="line-clamp-1 block">{h.question}</span>
            <span className="text-xs text-slate-400">{new Date(h.created_at).toLocaleString()}</span>
          </button>
        ))}
      </div>
    </Card>
  );
}
