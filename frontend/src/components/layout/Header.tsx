export function Header() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 font-mono text-sm font-bold text-white">
            SQL
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-900">SQL Database Agent</h1>
            <p className="text-xs text-slate-500">Natural-language → SQL → Insight</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          Connected
        </div>
      </div>
    </header>
  );
}
