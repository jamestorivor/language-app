import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import App from "../src/App";
import { LanguageProvider } from "../src/i18n";
import * as studyApi from "../src/api/study";

vi.mock("../src/api/study", async (importOriginal) => ({
  ...await importOriginal<typeof import("../src/api/study")>(),
  getStudyCards: vi.fn().mockResolvedValue([]),
  getStudySettings: vi.fn().mockResolvedValue({ retention_percent: 90, maximum_interval: 36500, fuzzing: true, shortcuts: { show_answer: "Enter", again: "a", hard: "s", good: "d", easy: "f" } }),
}));

afterEach(() => { cleanup(); localStorage.clear(); vi.clearAllMocks(); });

it("starts a review in the selected language and offers links to podcasts and study", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><LanguageProvider><App /></LanguageProvider></MemoryRouter>);
  const main = screen.getByRole("main");
  expect(within(main).getByRole("link", { name: "My podcasts" }).getAttribute("href")).toBe("/podcasts");
  expect(within(main).getByRole("link", { name: "Study" }).getAttribute("href")).toBe("/study");
  expect(within(main).queryByRole("heading", { name: "Mark words you already know" })).toBeNull();
  await user.click(within(main).getByRole("button", { name: "English" }));
  await user.click(within(main).getByRole("link", { name: "Start English review" }));
  await waitFor(() => expect(studyApi.getStudyCards).toHaveBeenCalledWith({ dueOnly: true, language: "en" }));
});
