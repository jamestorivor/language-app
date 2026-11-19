import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import MarkKnown from "../src/components/MarkKnown";
import { LanguageProvider } from "../src/i18n";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });

it("shows current progress, previews included levels, and refreshes after marking", async () => {
  let marked = false;
  vi.stubGlobal("fetch", vi.fn(async (_url: URL, init: RequestInit) => {
    if (init.method === "POST") {
      expect(JSON.parse(init.body as string)).toEqual({ language: "ja", level: "N4" });
      marked = true;
      return new Response(JSON.stringify({ matched_words: 3 }), { status: 200 });
    }
    return new Response(JSON.stringify([
      { level: "N5", known: 2, total: 2 },
      { level: "N4", known: marked ? 1 : 0, total: 1 },
      { level: "N3", known: 0, total: 0 },
      { level: "N2", known: 0, total: 0 },
      { level: "N1", known: 0, total: 0 },
    ]), { status: 200 });
  }));
  const user = userEvent.setup();
  render(<LanguageProvider><MarkKnown /></LanguageProvider>);
  expect(await screen.findByText("Fully marked through N5")).toBeTruthy();
  expect(screen.getByText("0 / 1 known").parentElement?.textContent).toContain("N4");
  await user.selectOptions(screen.getByRole("combobox", { name: "JLPT level" }), "N4");
  expect(screen.getByText("This will mark words in: N5, N4.")).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Mark as known" }));
  await waitFor(() => expect(screen.getByText("Fully marked through N4")).toBeTruthy());
  expect(screen.getByRole("status").textContent).toBe("Marked 3 words as known.");
});
