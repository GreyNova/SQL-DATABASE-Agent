import { useCallback, useRef, useState } from "react";
import type { ChatRequest, ChatStep, ChatResponse, StreamEvent } from "@/types";

interface StreamState {
  steps: ChatStep[];
  result: ChatResponse | null;
  error: string | null;
  isStreaming: boolean;
}

const INITIAL: StreamState = { steps: [], result: null, error: null, isStreaming: false };

/**
 * Streams /chat/stream (SSE). Returns state plus a `send` callback.
 * Each `step` event is appended to `steps`; the final `done` event sets `result`.
 */
export function useChatStream() {
  const [state, setState] = useState<StreamState>(INITIAL);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => setState(INITIAL), []);

  const send = useCallback(async (req: ChatRequest) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setState({ ...INITIAL, isStreaming: true });

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
        signal: ctrl.signal,
      });
      
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Server error ${res.status}: ${errText}`);
      }
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by a blank line (either \n\n or \r\n\r\n).
        const frames = buffer.split(/\r?\n\r?\n/);
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const evt = parseSseFrame(frame);
          if (!evt) continue;
          setState((prev) => reduce(prev, evt));
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setState((prev) => ({
        ...prev,
        isStreaming: false,
        error: (e as Error).message,
      }));
    } finally {
      setState((prev) => prev.isStreaming ? { ...prev, isStreaming: false } : prev);
    }
  }, []);

  const cancel = useCallback(() => abortRef.current?.abort(), []);

  return { ...state, send, cancel, reset };
}

// ---------------------------------------------------------------------------
function reduce(prev: StreamState, evt: StreamEvent): StreamState {
  switch (evt.event) {
    case "step":
      return { ...prev, steps: [...prev.steps, evt.data] };
    case "done":
      return { ...prev, result: evt.data, isStreaming: false };
    case "error":
      return {
        ...prev,
        isStreaming: false,
        error: evt.data.detail || evt.data.error,
      };
    default:
      return prev;
  }
}

function parseSseFrame(frame: string): StreamEvent | null {
  let event = "message";
  let data = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return null;
  try {
    const parsed = JSON.parse(data);
    return { event, data: parsed } as StreamEvent;
  } catch {
    return null;
  }
}
