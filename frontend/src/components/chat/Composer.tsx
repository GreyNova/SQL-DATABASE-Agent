import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/primitives";

const SUGGESTIONS = [
  "Top 10 selling products",
  "Revenue by month",
  "Which customer spent the most money?",
  "Show low stock products",
  "Which city generates highest revenue?",
];

export function Composer({
  onSend,
  disabled,
}: {
  onSend: (q: string) => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const q = value.trim();
    if (!q) return;
    onSend(q);
    setValue("");
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSend(s)}
            disabled={disabled}
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 shadow-sm transition hover:border-brand-300 hover:text-brand-700 disabled:opacity-50"
          >
            {s}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="flex items-center gap-2">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask a question about your sales data…"
          disabled={disabled}
          className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm shadow-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
        <Button type="submit" disabled={disabled || !value.trim()}>
          {disabled ? "Thinking…" : "Ask →"}
        </Button>
      </form>
    </div>
  );
}
