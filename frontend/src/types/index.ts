// Types mirroring the backend Pydantic schemas (app/models/schemas.py).
// Keep these in sync when the backend contract changes.

export interface ColumnMeta {
  name: string;
  type: string;
}

export type ChartType = "table" | "bar" | "line" | "pie" | "kpi";

export interface ChartSpec {
  type: ChartType;
  title: string;
  x_field?: string | null;
  y_field?: string | null;
  label_field?: string | null;
  value_field?: string | null;
}

export interface QueryExecution {
  sql: string;
  rowcount: number;
  columns: ColumnMeta[];
  rows: Record<string, unknown>[];
}

export interface ChatStep {
  node: string;
  status: "ok" | "error" | "skipped";
  message?: string | null;
  payload?: Record<string, unknown> | null;
  duration_ms?: number | null;
}

export interface ChatResponse {
  answer: string;
  sql?: string | null;
  execution?: QueryExecution | null;
  chart?: ChartSpec | null;
  steps: ChatStep[];
  follow_ups: string[];
  thread_id: string;
}

export interface ChatRequest {
  question: string;
  thread_id?: string;
  sample_size?: number;
}

export interface HistoryItem {
  id: string;
  thread_id: string;
  question: string;
  answer: string;
  sql?: string | null;
  rowcount?: number | null;
  created_at: string;
}

export interface HistoryListResponse {
  items: HistoryItem[];
  total: number;
}

// SSE streaming events emitted by /chat/stream
export type StreamEvent =
  | { event: "step"; data: ChatStep }
  | { event: "done"; data: ChatResponse }
  | { event: "error"; data: { error: string; detail?: string } };
