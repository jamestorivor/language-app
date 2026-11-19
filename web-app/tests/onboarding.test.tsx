import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { LanguageProvider } from "../src/i18n";
import { StudyLanguageProvider } from "../src/StudyLanguageProvider";
import { useStudyLanguage } from "../src/utils/studyLanguage";

afterEach(() => { cleanup(); localStorage.clear(); vi.unstubAllGlobals(); });

function App() {
  const [language] = useStudyLanguage();
  return <p>Learning: {language}</p>;
}

function renderApp() {
  return render(<LanguageProvider><StudyLanguageProvider><App /></StudyLanguageProvider></LanguageProvider>);
}

it.each([["English", "en", "CEFR level", "A2"], ["日本語", "ja", "JLPT level", "N4"]])("lets a new account choose %s and a starting level", async (label, choice, _levelLabel, level) => {
  let language = "ja";
  let onboarding = true;
  const fetcher = vi.fn(async (_url: URL, init: RequestInit = {}) => {
    if (init.method === "POST") {
      const body = JSON.parse(init.body as string);
      expect(body).toEqual({ learning_language: choice, level });
      language = body.learning_language;
      onboarding = false;
    }
    return Response.json({ learning_language: language, onboarding_required: onboarding });
  });
  vi.stubGlobal("fetch", fetcher);
  const user = userEvent.setup();
  const view = renderApp();
  expect(await screen.findByRole("heading", { name: "What would you like to learn?" })).toBeTruthy();
  const continueButton = screen.getByRole("button", { name: "Continue" }) as HTMLButtonElement;
  expect(continueButton.disabled).toBe(true);
  await user.click(screen.getByRole("radio", { name: new RegExp(label) }));
  await user.selectOptions(screen.getByRole("combobox", { name: "Words you already know (optional)" }), level);
  expect(screen.getByText(/This will mark words in:/).textContent).toContain(level);
  await user.click(continueButton);
  expect(await screen.findByText(`Learning: ${choice}`)).toBeTruthy();
  expect(fetcher.mock.calls.filter(([, init]) => init.method === "POST")).toHaveLength(1);
  view.unmount();
  renderApp();
  expect(await screen.findByText(`Learning: ${choice}`)).toBeTruthy();
  expect(screen.queryByRole("heading", { name: "What would you like to learn?" })).toBeNull();
});

it("keeps the choice on the page and allows retry when saving fails", async () => {
  let fail = true;
  vi.stubGlobal("fetch", vi.fn(async (_url: URL, init: RequestInit = {}) => {
    if (init.method === "POST") {
      expect(JSON.parse(init.body as string)).toEqual({ learning_language: "en", level: null });
      if (fail) return new Response("", { status: 500 });
    }
    return Response.json({ learning_language: "ja", onboarding_required: true });
  }));
  const user = userEvent.setup();
  renderApp();
  await user.click(await screen.findByRole("radio", { name: "English" }));
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect((await screen.findByRole("alert")).textContent).toContain("Could not complete setup");
  expect((screen.getByRole("radio", { name: "English" }) as HTMLInputElement).checked).toBe(true);
  fail = false;
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect(await screen.findByText("Learning: en")).toBeTruthy();
});

it("resets the level when the language changes", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ learning_language: "ja", onboarding_required: true })));
  const user = userEvent.setup();
  renderApp();
  await user.click(await screen.findByRole("radio", { name: "English" }));
  await user.selectOptions(screen.getByRole("combobox"), "A2");
  await user.click(screen.getByRole("radio", { name: /日本語/ }));
  const levels = screen.getByRole("combobox") as HTMLSelectElement;
  expect(levels.value).toBe("");
  expect(screen.getByRole("option", { name: "JLPT N5" })).toBeTruthy();
  expect(screen.queryByRole("option", { name: "CEFR A2" })).toBeNull();
});
