import { createClerkClient } from "@clerk/chrome-extension/client";

export async function authenticatedFetch(input: URL, init: RequestInit): Promise<Response> {
  const publishableKey = import.meta.env.WXT_CLERK_PUBLISHABLE_KEY;
  if (!publishableKey) throw new Error("Clerk is not configured for this extension");
  const clerk = await createClerkClient({ publishableKey, background: true });
  const token = await clerk.session?.getToken();
  if (!token) throw new Error("Sign in through the extension before parsing a page");
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}
