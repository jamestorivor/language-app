import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import App from "../src/App";
import { LanguageProvider } from "../src/i18n";
import { StudyLanguageProvider } from "../src/StudyLanguageProvider";
import * as studyApi from "../src/api/study";

vi.mock("../src/api/study", async (original) => ({
  ...await original<typeof import("../src/api/study")>(),
  getStudyCards: vi.fn().mockResolvedValue([]),
  getStudySettings: vi.fn().mockResolvedValue({ shortcuts: {} }),
}));
vi.mock("../src/api/podcast", async (original) => ({
  ...await original<typeof import("../src/api/podcast")>(),
  getEpisodes: vi.fn().mockResolvedValue([]),
}));

afterEach(() => { cleanup(); localStorage.clear(); vi.unstubAllGlobals(); vi.clearAllMocks(); });

function app(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><LanguageProvider><StudyLanguageProvider><App /></StudyLanguageProvider></LanguageProvider></MemoryRouter>);
}

it("saves the profile choice and uses it for vocabulary, podcasts, and review after reload", async () => {
  let saved = "ja";
  vi.stubGlobal("fetch", vi.fn(async (url: URL, init: RequestInit = {}) => {
    if (url.pathname.endsWith("/profile")) {
      if (init.method === "PUT") saved = JSON.parse(init.body as string).learning_language;
      return Response.json({ learning_language: saved });
    }
    if (url.pathname.endsWith("/known-count")) return Response.json({ count: 0 });
    if (url.pathname.endsWith("/mark-known")) return Response.json([]);
    throw new Error("Unexpected request");
  }));
  const user = userEvent.setup();
  const view = app("/settings");
  const languages = await screen.findByRole("group", { name: "Choose the language you are learning" });
  const confirm = screen.getByRole("button", { name: "Confirm language change" });
  expect((confirm as HTMLButtonElement).disabled).toBe(true);
  await user.click(within(languages).getByRole("button", { name: "English" }));
  expect(within(languages).getByRole("button", { name: "English" }).getAttribute("aria-pressed")).toBe("true");
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(saved).toBe("ja");
  await user.click(confirm);
  expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "Start English review" })).toBeTruthy();
  expect(saved).toBe("en");
  view.unmount();
  const library = app("/podcasts");
  expect(await screen.findByRole("heading", { name: "No English episodes yet" })).toBeTruthy();
  expect(screen.queryByRole("group", { name: "Podcast language" })).toBeNull();
  await user.click(screen.getByRole("link", { name: "Add a podcast", exact: true }));
  expect((screen.getByRole("combobox", { name: "Podcast language" }) as HTMLSelectElement).value).toBe("en");
  library.unmount();
  app("/study/review");
  await waitFor(() => expect(studyApi.getStudyCards).toHaveBeenCalledWith({ dueOnly: true, language: "en" }));
});

it("keeps the previous language visible when saving fails", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: URL, init: RequestInit = {}) => {
    if (url.pathname.endsWith("/profile")) return init.method === "PUT" ? new Response("", { status: 500 }) : Response.json({ learning_language: "ja" });
    if (url.pathname.endsWith("/known-count")) return Response.json({ count: 0 });
    if (url.pathname.endsWith("/mark-known")) return Response.json([]);
    throw new Error("Unexpected request");
  }));
  const user = userEvent.setup();
  app("/settings");
  const languages = await screen.findByRole("group", { name: "Choose the language you are learning" });
  await user.click(within(languages).getByRole("button", { name: "English" }));
  await user.click(screen.getByRole("button", { name: "Confirm language change" }));
  expect(await screen.findByText("Could not save your learning language. Please try again.")).toBeTruthy();
  expect(within(languages).getByRole("button", { name: "English" }).getAttribute("aria-pressed")).toBe("true");
  expect(screen.getByRole("combobox", { name: "JLPT level" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "User settings" })).toBeTruthy();
});


it("explains when the backend cannot authenticate sign-ins", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "Authentication is not configured" }), { status: 503 })));
  app("/");
  expect(await screen.findByText(/server is not configured for sign-in/i)).toBeTruthy();
});


it("does not save or redirect when the selection is reverted", async () => {
  const fetcher = vi.fn(async (url: URL, init: RequestInit = {}) => {
    if (url.pathname.endsWith("/profile")) {
      expect(init.method).not.toBe("PUT");
      return Response.json({ learning_language: "ja" });
    }
    if (url.pathname.endsWith("/known-count")) return Response.json({ count: 0 });
    if (url.pathname.endsWith("/mark-known")) return Response.json([]);
    throw new Error("Unexpected request");
  });
  vi.stubGlobal("fetch", fetcher);
  const user = userEvent.setup();
  app("/settings");
  const languages = await screen.findByRole("group", { name: "Choose the language you are learning" });
  await user.click(within(languages).getByRole("button", { name: "English" }));
  expect((screen.getByRole("button", { name: "Confirm language change" }) as HTMLButtonElement).disabled).toBe(false);
  await user.click(within(languages).getByRole("button", { name: "日本語" }));
  expect((screen.getByRole("button", { name: "Confirm language change" }) as HTMLButtonElement).disabled).toBe(true);
  expect(within(languages).getByRole("button", { name: "日本語" }).getAttribute("aria-pressed")).toBe("true");
  expect(screen.getByRole("heading", { name: "User settings" })).toBeTruthy();
  expect(fetcher.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(false);
});

it("shows the saved profile level and allows it to be changed without marking words", async () => {
  let level: string | null = "N4";
  const fetcher = vi.fn(async (url: URL, init: RequestInit = {}) => {
    if (url.pathname.endsWith("/profile/level")) {
      expect(JSON.parse(init.body as string)).toEqual({ language: "ja", level: "N3" });
      level = "N3";
      return Response.json({ language: "ja", level });
    }
    if (url.pathname.endsWith("/profile")) return Response.json({ learning_language: "ja", levels: { ja: level, en: "B1" } });
    if (url.pathname.endsWith("/known-count")) return Response.json({ count: 0 });
    if (url.pathname.endsWith("/mark-known")) return Response.json([]);
    throw new Error("Unexpected request");
  });
  vi.stubGlobal("fetch", fetcher);
  const user = userEvent.setup();
  const view = app("/settings");
  expect(await screen.findByText("N4", { selector: "strong" })).toBeTruthy();
  await user.selectOptions(screen.getByRole("combobox", { name: "Choose your profile level" }), "N3");
  await user.click(screen.getByRole("button", { name: "Save level" }));
  expect(await screen.findByText("N3", { selector: "strong" })).toBeTruthy();
  expect(fetcher.mock.calls.some(([url, init]) => url.pathname.endsWith("/mark-known") && init?.method === "POST")).toBe(false);
  view.unmount();
  app("/settings");
  expect(await screen.findByText("N3", { selector: "strong" })).toBeTruthy();
});
