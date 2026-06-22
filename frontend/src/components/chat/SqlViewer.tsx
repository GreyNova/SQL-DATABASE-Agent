import { useState } from "react";
import { Button } from "@/components/ui/primitives";

export function SqlViewer({ sql }: { sql: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="relative">
      <pre className="scroll-thin overflow-auto rounded-lg bg-slate-900 p-4 text-xs leading-relaxed text-slate-100">
        <code>{sql}</code>
      </pre>
      <Button variant="outline" onClick={copy} className="absolute right-2 top-2 px-2 py-1 text-xs">
        {copied ? "Copied!" : "Copy"}
      </Button>
    </div>
  );
}
