import { API_BASE_URL } from "@/lib/config";
import type { AnalysisInfo, Source } from "@/lib/types";

export interface AskStreamHandlers {
  onSources?: (query: string, sources: Source[]) => void;
  onToken?: (text: string) => void;
  onDone?: (answerFound: boolean) => void;
  onError?: (message: string) => void;
}

export interface AnalyzeStreamHandlers {
  onInfo?: (info: AnalysisInfo) => void;
  onToken?: (text: string) => void;
  onDone?: () => void;
  onError?: (message: string) => void;
}

/**
 * POST `/api/ask` and parse the Server-Sent Events response, invoking
 * the matching handler as each event arrives.
 *
 * WHY A HAND-ROLLED PARSER, NOT THE BROWSER'S `EventSource`
 * -------------------------------------------------------------
 * `EventSource` only supports GET requests with no body — this endpoint
 * needs POST (the question goes in a JSON body; a real legal question
 * can be long, and forcing it into a URL query string would need
 * awkward encoding for no benefit). `fetch()` + a `ReadableStream`
 * reader gives full control over the request while still consuming the
 * exact `text/event-stream` format the backend sends — see
 * `api/routers/ask.py`'s own docstring for why SSE was chosen there and
 * what the four event types (`sources`/`token`/`done`/`error`) mean.
 *
 * WHY NON-2XX RESPONSES ARE HANDLED SEPARATELY FROM SSE PARSING
 * -----------------------------------------------------------------------
 * A 400 (empty query) or 503 (Ollama unreachable) response is a normal
 * JSON body (`{"detail": "..."}`), not an SSE stream — `api/routers/
 * ask.py` raises these BEFORE constructing the `StreamingResponse`
 * specifically so the HTTP status code is meaningful (see that file's
 * docstring on why validation happens before the stream starts). This
 * function checks `response.ok` first and routes to `onError` with the
 * parsed message rather than trying to SSE-parse a JSON error body.
 */
export async function streamAsk(
  query: string,
  handlers: AskStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
    signal,
  });

  await consumeSSEResponse(response, (rawEvent) => dispatchAskEvent(rawEvent, handlers), handlers.onError);
}

/**
 * POST `/api/analyze-document` (a `File`, as `multipart/form-data`) and
 * parse the SSE response — same event-stream shape and same reasoning
 * for a hand-rolled parser over `EventSource` as `streamAsk` above (see
 * its docstring), plus `EventSource` can't send a file body at all.
 * `FormData` lets the browser set the multipart boundary itself; setting
 * `Content-Type` manually here would omit that boundary and break parsing
 * server-side.
 */
export async function streamAnalyzeDocument(
  file: File,
  handlers: AnalyzeStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/analyze-document`, {
    method: "POST",
    body: formData,
    signal,
  });

  await consumeSSEResponse(
    response,
    (rawEvent) => dispatchAnalyzeEvent(rawEvent, handlers),
    handlers.onError,
  );
}

/** Shared response-validation + SSE read loop for both streaming endpoints above. */
async function consumeSSEResponse(
  response: Response,
  onRawEvent: (rawEvent: string) => void,
  onError?: (message: string) => void,
): Promise<void> {
  if (!response.ok) {
    onError?.(await extractErrorMessage(response));
    return;
  }

  if (!response.body) {
    onError?.("Serverdan javob olinmadi (boʻsh stream).");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      onRawEvent(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
  }
}

function dispatchAnalyzeEvent(rawEvent: string, handlers: AnalyzeStreamHandlers): void {
  const lines = rawEvent.split("\n");
  const eventLine = lines.find((line) => line.startsWith("event: "));
  const dataLine = lines.find((line) => line.startsWith("data: "));
  if (!eventLine || !dataLine) return;

  const event = eventLine.slice("event: ".length);
  const data = JSON.parse(dataLine.slice("data: ".length));

  switch (event) {
    case "info":
      handlers.onInfo?.(data as AnalysisInfo);
      break;
    case "token":
      handlers.onToken?.(data.text as string);
      break;
    case "done":
      handlers.onDone?.();
      break;
    case "error":
      handlers.onError?.(data.message as string);
      break;
  }
}

function dispatchAskEvent(rawEvent: string, handlers: AskStreamHandlers): void {
  const lines = rawEvent.split("\n");
  const eventLine = lines.find((line) => line.startsWith("event: "));
  const dataLine = lines.find((line) => line.startsWith("data: "));
  if (!eventLine || !dataLine) return;

  const event = eventLine.slice("event: ".length);
  const data = JSON.parse(dataLine.slice("data: ".length));

  switch (event) {
    case "sources":
      handlers.onSources?.(data.query as string, data.sources as Source[]);
      break;
    case "token":
      handlers.onToken?.(data.text as string);
      break;
    case "done":
      handlers.onDone?.(data.answer_found as boolean);
      break;
    case "error":
      handlers.onError?.(data.message as string);
      break;
  }
}

/** FastAPI's default error shape: `{"detail": string}` for HTTPException, `{"detail": [...]}` for Pydantic validation (422). */
async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        const messages = detail
          .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : null))
          .filter((msg): msg is string => Boolean(msg));
        if (messages.length) return messages.join("; ");
      }
    }
  } catch {
    // response body wasn't JSON - fall through to the generic message below
  }
  return `Server xatosi (${response.status}).`;
}
