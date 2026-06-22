import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartSpec } from "@/types";
import { formatCell } from "@/utils/format";

const PALETTE = ["#3b6cf6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

export function Chart({ spec, rows }: { spec: ChartSpec; rows: Record<string, unknown>[] }) {
  if (!rows.length) return null;

  if (spec.type === "kpi") {
    const val = formatCell(rows[0][spec.value_field!]);
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <span className="text-4xl font-bold text-brand-600">{val}</span>
        <span className="mt-1 text-sm text-slate-500">{spec.title}</span>
      </div>
    );
  }

  if (spec.type === "pie") {
    const label = spec.label_field!;
    const value = spec.value_field!;
    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={rows} dataKey={value} nameKey={label} cx="50%" cy="50%" outerRadius={100} label>
            {rows.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  const x = spec.x_field!;
  const y = spec.y_field!;
  const common = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
      <XAxis dataKey={x} tick={{ fontSize: 12 }} />
      <YAxis tick={{ fontSize: 12 }} />
      <Tooltip />
    </>
  );

  if (spec.type === "line") {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={rows}>
          {common}
          <Line type="monotone" dataKey={y} stroke="#3b6cf6" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  // bar (default)
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={rows}>
        {common}
        <Bar dataKey={y} fill="#3b6cf6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
