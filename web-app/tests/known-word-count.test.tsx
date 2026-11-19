import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/components/Home";
import { LanguageProvider } from "../src/i18n";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });

it("shows the known count for the selected learning language", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: URL) => new Response(JSON.stringify({
    count: url.searchParams.get("language") === "ja" ? 1234 : 56,
  }), { status: 200 })));
  localStorage.setItem("study-language", "en");
  render(<LanguageProvider><MemoryRouter><Home /></MemoryRouter></LanguageProvider>);
  expect(screen.queryByRole("button", { name: "English" })).toBeNull();
  expect(await screen.findByText("56 known words")).toBeTruthy();
  expect(screen.getByText("English · Words rated 4 or 5")).toBeTruthy();
});
