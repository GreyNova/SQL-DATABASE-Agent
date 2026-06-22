import { Badge, Button, Card } from "@/components/ui/primitives";
import { Chart } from "@/components/chart/Chart";
import { ResultTable, ThoughtStream } from "@/components/chat/ResultTable";
import { SqlViewer } from "@/components/chat/SqlViewer";
import { downloadCsv, formatCell } from "@/utils/format";
import type { ChatResponse } from "@/types";
import { useState } from "react";

const TABS = ["answer", "table", "chart", "sql", "steps"] as const;
type Tab = (typeof TABS)[number];

export function AnswerCard({
  response,
  onFollowUp,
}: {
  response: ChatResponse;
  onFollowUp: (q: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("answer");
  const [showSql, setShowSql] = useState(true);
  const exec = response.execution ?? undefined;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-1 border-b border-slate-200 px-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`relative px-3 py-2.5 text-sm font-medium capitalize transition ${
              tab === t ? "text-brand-600" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
            {t === "table" && exec && <Badge tone="slate">{exec.rowcount}</Badge>}
            {tab === t && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded bg-brand-600" />}
          </button>
        ))}
      </div>

      <div className="p-5">
        {tab === "answer" && (
          <div className="space-y-4">
            <p className="text-[15px] leading-relaxed text-slate-800">{response.answer}</p>
            {response.follow_ups.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-2">
                {response.follow_ups.map((q) => (
                  <button
                    key={q}
                    onClick={() => onFollowUp(q)}
                    className="rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-xs text-brand-700 hover:bg-brand-100"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "table" && exec && <ResultTable execution={exec} />}

        {tab === "chart" && response.chart && exec && (
          <div>
            <h3 className="mb-3 text-sm font-semibold text-slate-700">{response.chart.title}</h3>
            <Chart spec={response.chart} rows={exec.rows} />
          </div>
        )}

        {tab === "sql" && response.sql && <SqlViewer sql={response.sql} />}

        {tab === "steps" && <ThoughtStream steps={response.steps} />}
      </div>

      {exec && (
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-5 py-2.5">
          <span className="text-xs text-slate-500">
            {exec.rowcount} row(s) · {exec.columns.length} column(s)
          </span>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => setShowSql((s) => !s)} className="px-2 py-1 text-xs">
              {showSql ? "Hide" : "Show"} SQL
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                downloadCsv("query_result.csv", exec.columns.map((c) => c.name), exec.rows)
              }
              className="px-2 py-1 text-xs"
            >
              Export CSV
            </Button>
          </div>
        </div>
      )}

      {showSql && response.sql && tab !== "sql" && (
        <div className="border-t border-slate-200 p-3">
          <SqlViewer sql={response.sql} />
        </div>
      )}
    </Card>
  );
}

export { formatCell };
