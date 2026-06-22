import { useCallback, useState } from "react";
import { Header } from "@/components/layout/Header";
import { Composer } from "@/components/chat/Composer";
import { AnswerCard } from "@/components/chat/AnswerCard";
import { HistorySidebar } from "@/components/chat/HistorySidebar";
import { ThoughtStream } from "@/components/chat/ResultTable";
import { Card } from "@/components/ui/primitives";
import { useChatStream } from "@/hooks/useChatStream";
import { useQueryClient } from "@tanstack/react-query";
import type { ChatResponse } from "@/types";

export default function App() {
  const stream = useChatStream();
  const qc = useQueryClient();
  const [threadId, setThreadId] = useState<string | undefined>();

  const send = useCallback(
    (question: string) => {
      stream.send({ question, thread_id: threadId });
    },
    [stream, threadId]
  );

  const onDone = useCallback(
    (res: ChatResponse) => {
      setThreadId(res.thread_id);
      qc.invalidateQueries({ queryKey: ["history"] });
    },
    [qc]
  );

  // When a streamed response arrives, capture its thread_id + refresh history.
  const finalResponse = stream.result;
  if (finalResponse && finalResponse.thread_id !== threadId) {
    onDone(finalResponse);
  }

  const pickHistory = useCallback(
    (question: string, tid?: string) => {
      setThreadId(tid);
      stream.reset();
      stream.send({ question, thread_id: tid });
    },
    [stream]
  );

  return (
    <div className="flex h-screen flex-col">
      <Header />
      <main className="mx-auto flex w-full max-w-7xl flex-1 gap-6 overflow-hidden p-6">
        {/* Sidebar */}
        <aside className="hidden w-72 shrink-0 md:block">
          <HistorySidebar onPick={pickHistory} activeThreadId={threadId} />
        </aside>

        {/* Main column */}
        <section className="flex flex-1 flex-col gap-4 overflow-hidden">
          <Card className="p-5">
            <Composer onSend={send} disabled={stream.isStreaming} />
          </Card>

          <div className="scroll-thin flex-1 space-y-4 overflow-auto pb-4">
            {/* Live thought-stream while streaming */}
            {stream.isStreaming && stream.steps.length > 0 && (
              <Card className="p-4">
                <ThoughtStream steps={stream.steps} />
              </Card>
            )}

            {stream.error && (
              <Card className="border-red-200 bg-red-50 p-4">
                <p className="text-sm text-red-700">⚠ {stream.error}</p>
              </Card>
            )}

            {finalResponse && (
              <AnswerCard response={finalResponse} onFollowUp={send} />
            )}

            {!finalResponse && !stream.isStreaming && !stream.error && (
              <EmptyState />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function EmptyState() {
  return (
    <Card className="flex flex-col items-center justify-center gap-3 p-12 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-2xl">
        💬
      </div>
      <h2 className="text-lg font-semibold text-slate-800">Ask anything about your data</h2>
      <p className="max-w-md text-sm text-slate-500">
        I&apos;ll read the schema, write and validate safe SQL, run it against the read-only
        database, and explain the results in plain English.
      </p>
    </Card>
  );
}
