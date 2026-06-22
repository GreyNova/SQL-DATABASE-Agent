import { Badge } from "@/components/ui/primitives";
import { formatCell } from "@/utils/format";
import type { QueryExecution } from "@/types";

const NODE_LABELS: Record<string, string> = {
  schema_discovery: "Schema Discovery",
  sql_generator: "SQL Generator",
  sql_validator: "SQL Validator",
  sql_repair: "SQL Repair",
  query_executor: "Query Executor",
  result_explainer: "Result Explainer",
};

export function ResultTable({ execution }: { execution: QueryExecution }) {
  const cols = execution.columns.map((c) => c.name);
  return (
    <div className="scroll-thin max-h-96 overflow-auto">
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0 bg-slate-50">
          <tr>
            {cols.map((c) => (
              <th key={c} className="border-b border-slate-200 px-3 py-2 text-left font-semibold text-slate-600">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {execution.rows.map((row, i) => (
            <tr key={i} className="hover:bg-slate-50">
              {cols.map((c) => (
                <td key={c} className="border-b border-slate-100 px-3 py-2 font-mono text-xs text-slate-700">
                  {formatCell(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ThoughtStream({ steps }: { steps: { node: string; status: string; message?: string | null; duration_ms?: number | null }[] }) {
  if (steps.length === 0) return null;
  return (
    <ol className="space-y-1.5">
      {steps.map((s, i) => (
        <li key={i} className="flex items-center gap-2 text-sm">
          <Badge tone={s.status === "ok" ? "green" : s.status === "error" ? "red" : "amber"}>
            {NODE_LABELS[s.node] ?? s.node}
          </Badge>
          <span className="text-slate-600">{s.message}</span>
          {s.duration_ms != null && <span className="text-xs text-slate-400">· {s.duration_ms}ms</span>}
        </li>
      ))}
    </ol>
  );
}
