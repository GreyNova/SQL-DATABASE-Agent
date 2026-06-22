/** Format values for display + CSV export. */
export function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toString() : value.toFixed(2);
  }
  return String(value);
}

/** Trigger a CSV download in the browser. */
export function downloadCsv(filename: string, columns: string[], rows: Record<string, unknown>[]) {
  const escape = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const header = columns.map(escape).join(",");
  const body = rows
    .map((r) => columns.map((c) => escape(formatCell(r[c]))).join(","))
    .join("\n");
  const blob = new Blob([`${header}\n${body}`], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
