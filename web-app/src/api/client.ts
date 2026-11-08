import "../logging";

/** Log request metadata only: never include payloads, URLs, or credentials. */
export async function loggedFetch(
  operation: string,
  input: URL,
  init: RequestInit = {},
): Promise<Response> {
  const requestId = globalThis.crypto?.randomUUID?.();
  const headers = new Headers(init.headers);
  if (requestId) headers.set("X-Request-ID", requestId);
  const started = performance.now();
  const method = init.method ?? "GET";
  try {
    const response = await fetch(input, { ...init, headers });
    const details = {
      operation,
      method,
      status: response.status,
      durationMs: Math.round(performance.now() - started),
      requestId: response.headers.get("X-Request-ID") ?? requestId,
    };
    if (response.ok) console.info("API request completed", details);
    else console.error("API request failed", details);
    return response;
  } catch (error) {
    console.error("API request failed", {
      operation,
      method,
      durationMs: Math.round(performance.now() - started),
      requestId,
      errorType: error instanceof Error ? error.name : "UnknownError",
    });
    throw error;
  }
}
