import "../logging";

let getSessionToken: (() => Promise<string | null>) | undefined;

export function setSessionTokenProvider(provider: (() => Promise<string | null>) | undefined) {
  getSessionToken = provider;
}

/** Log request metadata only: never include payloads, URLs, or credentials. */
export async function loggedFetch(
  operation: string,
  input: URL,
  init: RequestInit = {},
): Promise<Response> {
  const requestId = globalThis.crypto?.randomUUID?.();
  const headers = new Headers(init.headers);
  if (getSessionToken) {
    const token = await getSessionToken();
    if (!token) throw new Error("Please sign in to continue");
    headers.set("Authorization", `Bearer ${token}`);
  }
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
