import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import Study from "../src/components/Study";
import StudyHome from "../src/components/StudyHome";
import StudyList from "../src/components/StudyList";
import * as studyApi from "../src/api/study";
import * as japaneseApi from "../src/api/japanese";
import type { StudyCard, StudySource } from "../src/api/study";
import { defaultStudyShortcuts } from "../src/utils/studyShortcuts";

vi.mock("../src/api/study", () => ({
  getStudyCards: vi.fn(), getStudySettings: vi.fn(), getStudyStats: vi.fn(), getStudySources: vi.fn(), reviewStudyCard: vi.fn(), deleteStudyCard: vi.fn(), addStudyCard: vi.fn(), updateStudyCard: vi.fn(),
}));
vi.mock("../src/api/japanese", () => ({ updateWordFamiliarity: vi.fn() }));

const card = (overrides: Partial<StudyCard> = {}): StudyCard => ({
  id: 1, word_id: 7, target_text: "猫", reading: "ねこ", definitions: ["cat"],
  sentence: "猫がいます。", sentence_translation: null, episode_id: 10, segment_id: 11,
  episode_title: "Japanese Podcast", sentence_start: 0, sentence_end: 6, target_start: 0, target_end: 1,
  due_at: "2026-01-01T00:00:00Z", created_at: "2025-12-01T00:00:00Z", version: 2,
  state: "review", review_status: "normal", next_eligible_at: "2026-01-01T00:00:00Z",
  familiarity_level: 2, manual_level: 2, level_source: "manual", is_due: true, membership_active: true,
  ...overrides,
});

const source = (overrides: Partial<StudySource> = {}): StudySource => ({
  id: 42, card_id: 1, word_id: 7, episode_id: 10, episode_title: "Japanese Podcast", segment_id: 11,
  sentence: "猫がいます。", target_text: "猫", target_start: 0, target_end: 1, sentence_start: 0, sentence_end: 6,
  transcript_start: 0, transcript_end: 6, start_ms: 123000, end_ms: 126000, timing: "cue", source_status: "available",
  ...overrides,
});

const show = (view: React.ReactNode) => render(<MemoryRouter>{view}</MemoryRouter>);

beforeEach(() => {
  vi.resetAllMocks();
  localStorage.removeItem("study-language");
  vi.mocked(studyApi.getStudyCards).mockResolvedValue([card()]);
  vi.mocked(studyApi.getStudySettings).mockResolvedValue({ retention_percent: 90, maximum_interval: 36500, fuzzing: true, shortcuts: defaultStudyShortcuts });
  vi.mocked(studyApi.getStudyStats).mockResolvedValue({ due_count: 1, due_today_count: 1, completed_count: 0 });
  vi.mocked(studyApi.getStudySources).mockResolvedValue([source()]);
});
afterEach(cleanup);

describe("review", () => {
  it("hides the answer and rating controls until the user reveals it", async () => {
    const user = userEvent.setup();
    show(<Study />);
    expect(await screen.findByRole("heading", { name: "猫" })).toBeTruthy();
    expect(studyApi.getStudyCards).toHaveBeenCalledWith({ dueOnly: true, language: "ja" });
    expect(screen.getByText("ねこ")).toBeTruthy();
    expect(screen.getByLabelText("Familiarity 2 of 5")).toBeTruthy();
    expect(screen.queryByText("cat")).toBeNull();
    expect(screen.queryByText("猫がいます。")).toBeNull();
    expect(screen.queryByRole("link", { name: /Japanese Podcast/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Again/ })).toBeNull();
    expect(studyApi.reviewStudyCard).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Show answer" }));
    expect(screen.getByText("cat")).toBeTruthy();
    expect(screen.getByRole("region", { name: "Source sentence" }).textContent).toContain("猫がいます。");
    expect(screen.getByText("Source details").closest("details")?.open).toBe(false);
    await user.click(screen.getByText("Source details"));
    expect((await screen.findByRole("link", { name: "Listen in context" })).getAttribute("href")).toBe("/podcasts/segments/11?study_card=1&context=42");
    expect(studyApi.reviewStudyCard).not.toHaveBeenCalled();
  });

  it.each([["a", 1], ["s", 2], ["d", 3], ["f", 4]] as const)("reveals with Enter and grades %s as %i", async (key, rating) => {
    const user = userEvent.setup();
    vi.mocked(studyApi.reviewStudyCard).mockResolvedValue(card({ is_due: false, version: 3 }));
    show(<Study />);
    await screen.findByRole("heading", { name: "猫" });
    await user.keyboard(key);
    expect(studyApi.reviewStudyCard).not.toHaveBeenCalled();
    await user.keyboard("{Enter}");
    expect(screen.getByText("cat")).toBeTruthy();
    await user.keyboard(key);
    expect(studyApi.reviewStudyCard).toHaveBeenCalledOnce();
    expect(studyApi.reviewStudyCard).toHaveBeenCalledWith(1, rating, 2);
  });

  it("uses the saved shortcuts for revealing and grading", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.getStudySettings).mockResolvedValue({ retention_percent: 90, maximum_interval: 36500, fuzzing: true,
      shortcuts: { show_answer: "Space", again: "1", hard: "2", good: "3", easy: "ArrowRight" } });
    vi.mocked(studyApi.reviewStudyCard).mockResolvedValue(card({ is_due: false, version: 3 }));
    show(<Study />);
    await screen.findByRole("heading", { name: "猫" });
    await waitFor(() => expect(screen.getByRole("button", { name: "Show answer" }).getAttribute("aria-keyshortcuts")).toBe("Space"));
    await user.keyboard("{Enter}");
    expect(screen.queryByText("cat")).toBeNull();
    await user.keyboard(" ");
    expect(screen.getByText("cat")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Good: Remembered" }).getAttribute("aria-keyshortcuts")).toBe("3");
    await user.keyboard("3");
    expect(studyApi.reviewStudyCard).toHaveBeenCalledWith(1, 3, 2);
  });

  it("keeps buttons usable if shortcut settings fail to load", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.getStudySettings).mockRejectedValue(new Error("offline"));
    show(<Study />);
    expect((await screen.findByRole("alert")).textContent).toContain("Could not load keyboard shortcuts");
    await user.click(screen.getByRole("button", { name: "Show answer" }));
    expect(screen.getByText("cat")).toBeTruthy();
  });

  it("does not intercept typing, modified keys, or focused controls", async () => {
    const user = userEvent.setup();
    const { container } = show(<Study />);
    await screen.findByRole("heading", { name: "猫" });
    const input = document.createElement("input");
    container.appendChild(input);
    input.focus();
    await user.keyboard("{Enter}a");
    expect(screen.queryByText("cat")).toBeNull();
    input.blur();
    fireEvent.keyDown(document.body, { key: "Enter", ctrlKey: true });
    fireEvent.keyDown(document.body, { key: "Enter", repeat: true });
    expect(screen.queryByText("cat")).toBeNull();
    screen.getByRole("button", { name: "Refresh" }).focus();
    fireEvent.keyDown(screen.getByRole("button", { name: "Refresh" }), { key: "Enter" });
    expect(screen.queryByText("cat")).toBeNull();
    (document.activeElement as HTMLElement | null)?.blur();
    await user.keyboard("{Enter}");
    input.focus();
    await user.keyboard("a");
    fireEvent.keyDown(document.body, { key: "s", metaKey: true });
    fireEvent.keyDown(document.body, { key: "d", isComposing: true });
    expect(studyApi.reviewStudyCard).not.toHaveBeenCalled();
  });

  it("ignores repeated or additional shortcuts while a review is saving", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.reviewStudyCard).mockImplementation(() => new Promise(() => {}));
    show(<Study />);
    await screen.findByRole("heading", { name: "猫" });
    await user.keyboard("{Enter}");
    fireEvent.keyDown(document.body, { key: "a", repeat: true });
    expect(studyApi.reviewStudyCard).not.toHaveBeenCalled();
    await user.keyboard("a");
    await user.keyboard("sdf");
    expect(studyApi.reviewStudyCard).toHaveBeenCalledOnce();
  });

  it("submits only the selected grade and removes cards that are no longer due", async () => {
    const user = userEvent.setup();
    const updated = card({ familiarity_level: 3, next_eligible_at: "2026-02-01T00:00:00Z", is_due: false, version: 3 });
    vi.mocked(studyApi.reviewStudyCard).mockResolvedValue(updated);
    show(<Study />);
    await screen.findByRole("heading", { name: "猫" });
    await user.click(screen.getByRole("button", { name: "Show answer" }));
    vi.mocked(studyApi.getStudyCards).mockResolvedValue([]);
    vi.mocked(studyApi.getStudyStats).mockResolvedValue({ due_count: 0, due_today_count: 0, completed_count: 1 });
    await user.click(screen.getByRole("button", { name: "Good: Remembered" }));
    await screen.findByRole("heading", { name: "No cards are due right now" });
    expect(studyApi.reviewStudyCard).toHaveBeenCalledOnce();
    expect(studyApi.reviewStudyCard).toHaveBeenCalledWith(1, 3, 2);
    expect(screen.getByText(/Review saved. Next review:/)).toBeTruthy();
    expect(screen.getByText(/Familiarity is now level 3/)).toBeTruthy();
    expect(screen.queryByText("cat")).toBeNull();
  });

  it("does not count or remove a card when the review request fails", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.reviewStudyCard).mockRejectedValue(new Error("conflict"));
    show(<Study />);
    await screen.findByRole("heading", { name: "猫" });
    await user.click(screen.getByRole("button", { name: "Show answer" }));
    await user.click(screen.getByRole("button", { name: /Again:/ }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "猫" })).toBeTruthy();
    expect(screen.queryByText("cat")).toBeNull();
  });

  it("marks a word mastered without recording a review", async () => {
    const user = userEvent.setup();
    vi.mocked(japaneseApi.updateWordFamiliarity).mockResolvedValue({ word_id: 7, new_score: 5 });
    show(<Study />);
    await screen.findByRole("heading", { name: "猫" });
    vi.mocked(studyApi.getStudyCards).mockResolvedValue([]);
    await user.click(screen.getByRole("button", { name: "Mark as Mastered" }));
    await screen.findByRole("heading", { name: "No cards are due right now" });
    expect(japaneseApi.updateWordFamiliarity).toHaveBeenCalledWith(7, 5, "ja");
    expect(studyApi.reviewStudyCard).not.toHaveBeenCalled();
  });

  it("highlights only the selected surface form and switches to another source", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.getStudySources).mockResolvedValue([
      source({ sentence: "😀猫と猫。", target_start: 3, target_end: 4, dictionary_form: "猫" }),
      source({ id: 43, card_id: 2, episode_id: 12, episode_title: "Second episode", segment_id: 22,
        sentence: "猫を見た。", target_start: 0, target_end: 1, start_ms: 30000, end_ms: 34000 }),
    ]);
    show(<Study />);
    await screen.findByRole("heading", { name: "猫" });
    await user.click(screen.getByRole("button", { name: "Show answer" }));
    await user.click(screen.getByText("Source details"));
    const selector = await screen.findByRole("combobox", { name: "Source sentence" });
    const context = screen.getByRole("region", { name: "Source sentence" });
    const mark = context.querySelector("mark");
    expect(mark?.textContent).toBe("猫");
    expect(mark?.previousSibling?.textContent).toBe("😀猫と");
    expect(context.textContent).toContain("2:03");
    await user.selectOptions(selector, "43");
    expect(context.textContent).toContain("Second episode");
    expect(within(context).getByRole("link", { name: "Listen in context" }).getAttribute("href")).toBe("/podcasts/segments/22?study_card=2&context=43");
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
  });

  it("does not highlight mismatched offsets or promise precise playback when context changed", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.getStudySources).mockResolvedValue([source({ target_start: 1, target_end: 2, source_status: "changed", start_ms: null, end_ms: null, timing: "unknown" })]);
    show(<Study />);
    await screen.findByRole("heading", { name: "猫" });
    await user.click(screen.getByRole("button", { name: "Show answer" }));
    await user.click(screen.getByText("Source details"));
    expect(await screen.findByText(/transcript has changed/)).toBeTruthy();
    const context = screen.getByRole("region", { name: "Source sentence" });
    expect(context.querySelector("mark")).toBeNull();
    expect(within(context).getByText(/Timestamp unavailable/)).toBeTruthy();
    expect(within(context).getByRole("link", { name: "Open source segment" })).toBeTruthy();
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
  });

  it("keeps the saved sentence when its source episode has been deleted", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.getStudySources).mockResolvedValue([source({ episode_id: null, segment_id: null,
      source_status: "missing", start_ms: null, end_ms: null, timing: "unknown" })]);
    show(<Study />);
    await screen.findByRole("heading", { name: "猫" });
    await user.click(screen.getByRole("button", { name: "Show answer" }));
    await user.click(screen.getByText("Source details"));
    expect(await screen.findByText(/original segment or episode is no longer available/)).toBeTruthy();
    const context = screen.getByRole("region", { name: "Source sentence" });
    expect(context.textContent).toContain("猫がいます。");
    expect(within(context).queryByRole("link")).toBeNull();
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
  });
});

it("can retry loading study progress without blocking navigation", async () => {
  const user = userEvent.setup();
  vi.mocked(studyApi.getStudyStats).mockRejectedValueOnce(new Error("offline"));
  show(<StudyHome />);
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Start 日本語 review" })).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  expect(within(screen.getByRole("region", { name: "Today’s progress" })).getAllByText("1")).toHaveLength(2);
});

describe("Study List", () => {
  it("filters enrolled cards by status and familiarity without starting a review", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.getStudyCards).mockResolvedValue([
      card(),
      card({ id: 2, word_id: 8, target_text: "犬", reading: "いぬ", definitions: ["dog"], sentence: "犬がいます。", familiarity_level: 4, review_status: "deferred", is_due: false }),
      card({ id: 3, word_id: 9, target_text: "鳥", reading: "とり", definitions: ["bird"], sentence: "鳥がいます。", familiarity_level: 5, review_status: "mastered", is_due: false, next_eligible_at: null }),
    ]);
    show(<StudyList />);
    await screen.findByRole("heading", { name: "猫" });
    expect(studyApi.getStudyCards).toHaveBeenCalledWith({ includeRemoved: true, language: "ja" });
    await user.selectOptions(screen.getByRole("combobox", { name: "Status" }), "waiting");
    expect(screen.getByRole("heading", { name: "犬" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "猫" })).toBeNull();
    await user.selectOptions(screen.getByRole("combobox", { name: "Familiarity" }), "3");
    expect(screen.getByText("No cards match these filters.")).toBeTruthy();
    expect(studyApi.reviewStudyCard).not.toHaveBeenCalled();
  });

  it("reactivates mastered words only after the user chooses a level", async () => {
    const user = userEvent.setup();
    const mastered = card({ familiarity_level: 5, manual_level: 5, review_status: "mastered", next_eligible_at: null, is_due: false });
    vi.mocked(studyApi.getStudyCards).mockResolvedValue([mastered]);
    vi.mocked(japaneseApi.updateWordFamiliarity).mockResolvedValue({ word_id: 7, new_score: 3 });
    show(<StudyList />);
    const item = (await screen.findByRole("heading", { name: "猫" })).closest("li")!;
    await user.click(within(item).getByRole("button", { name: "Reactivate 猫" }));
    const confirm = within(item).getByRole("button", { name: "Confirm reactivation" }) as HTMLButtonElement;
    expect(confirm.disabled).toBe(true);
    await user.selectOptions(within(item).getByRole("combobox", { name: "New familiarity level" }), "3");
    await user.click(confirm);
    await waitFor(() => expect(japaneseApi.updateWordFamiliarity).toHaveBeenCalledWith(7, 3, "ja"));
    expect(studyApi.reviewStudyCard).not.toHaveBeenCalled();
  });

  it("requires confirmation before removing a card and keeps the review history", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.deleteStudyCard).mockResolvedValue(undefined);
    show(<StudyList />);
    await screen.findByRole("heading", { name: "猫" });
    await user.click(screen.getByRole("button", { name: "Remove 猫 from study" }));
    expect(studyApi.deleteStudyCard).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Confirm removal" }));
    await waitFor(() => expect(studyApi.deleteStudyCard).toHaveBeenCalledWith(1));
    expect(await screen.findByText(/review history is saved/)).toBeTruthy();
  });

  it("edits the card and shows the saved changes", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.updateStudyCard).mockResolvedValue(card({ reading: "ネコ", definitions: ["feline"], sentence: "猫が好きです。", version: 3 }));
    show(<StudyList />);
    await screen.findByRole("heading", { name: "猫" });
    await user.click(screen.getByRole("button", { name: "Edit 猫" }));
    await user.clear(screen.getByLabelText("Reading"));
    await user.type(screen.getByLabelText("Reading"), "ネコ");
    await user.clear(screen.getByLabelText(/Definitions/));
    await user.type(screen.getByLabelText(/Definitions/), "feline");
    await user.clear(screen.getByLabelText("Study sentence"));
    await user.type(screen.getByLabelText("Study sentence"), "猫が好きです。");
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(studyApi.updateStudyCard).toHaveBeenCalledWith(1, { version: 2, reading: "ネコ", definitions: ["feline"], sentence: "猫が好きです。" }));
    expect(await screen.findByText("feline")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "猫" }).closest("li")?.textContent).toContain("猫が好きです。");
    await user.click(screen.getByRole("button", { name: "View sources for 猫" }));
    expect(await screen.findByText("Original sentence")).toBeTruthy();
    expect(screen.getByRole("region", { name: "Source sentence" }).textContent).toContain("猫がいます。");
  });

  it("shows saved sources for removed cards without reenrolling them", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.getStudyCards).mockResolvedValue([card({ membership_active: false, is_due: false })]);
    show(<StudyList />);
    await screen.findByText("No cards match these filters.");
    await user.selectOptions(screen.getByRole("combobox", { name: "Status" }), "removed");
    await screen.findByRole("heading", { name: "猫" });
    expect(screen.queryByRole("button", { name: /Remove 猫/ })).toBeNull();
    await user.click(screen.getByRole("button", { name: "View sources for 猫" }));
    expect(await screen.findByRole("link", { name: "Listen in context" })).toBeTruthy();
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
    expect(studyApi.reviewStudyCard).not.toHaveBeenCalled();
  });
});


it("uses the learning language for the study page, reviews and study list", async () => {
  const user = userEvent.setup();
  localStorage.setItem("study-language", "en");
  const english = card({ id: -1, language: "en", target_text: "cat", reading: "", definitions: ["猫"] });
  vi.mocked(studyApi.getStudyCards).mockImplementation(async (options) => options?.language === "en" ? [english] : [card()]);
  vi.mocked(studyApi.getStudyStats).mockImplementation(async (_zone, language) => ({ due_count: language === "en" ? 3 : 1, due_today_count: 1, completed_count: 0 }));
  const routes = <Routes><Route path="/study" element={<StudyHome />} /><Route path="/study/review" element={<Study />} /><Route path="/study/list" element={<StudyList />} /><Route path="/study/settings" element={<h1>Study settings</h1>} /></Routes>;
  const view = render(<MemoryRouter initialEntries={["/study"]}>{routes}</MemoryRouter>);
  expect(screen.getByRole("heading", { name: "Study" })).toBeTruthy();
  expect(screen.getByRole("link", { name: /Study settings/ }).getAttribute("href")).toBe("/study/settings");
  expect(screen.getByRole("link", { name: /Study List/ }).getAttribute("href")).toBe("/study/list");
  expect(studyApi.getStudyCards).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "English" })).toBeNull();
  expect(screen.getByRole("link", { name: "Start English review" })).toBeTruthy();
  await waitFor(() => expect(within(screen.getByRole("region", { name: "Today’s progress" })).getByText("3")).toBeTruthy());
  await user.click(screen.getByRole("link", { name: "Start English review" }));
  await screen.findByRole("heading", { name: "cat" });
  expect(screen.queryByRole("heading", { name: "猫" })).toBeNull();
  expect(screen.queryByRole("button", { name: "English" })).toBeNull();
  expect(screen.queryByRole("region", { name: "Today’s progress" })).toBeNull();
  expect(screen.queryByRole("heading", { name: "Review" })).toBeNull();
  expect(screen.queryByRole("link", { name: /Study settings|Study List/ })).toBeNull();
  expect(studyApi.getStudyStats).toHaveBeenLastCalledWith(expect.any(String), "en");
  view.unmount();
  render(<MemoryRouter initialEntries={["/study"]}>{routes}</MemoryRouter>);
  expect(screen.queryByRole("button", { name: "English" })).toBeNull();
  await user.click(screen.getByRole("link", { name: /Study List/ }));
  await screen.findByRole("heading", { name: "cat" });
  expect(studyApi.getStudyCards).toHaveBeenLastCalledWith({ includeRemoved: true, language: "en" });
  expect(screen.queryByRole("button", { name: "English" })).toBeNull();
  expect(screen.queryByRole("button", { name: "日本語" })).toBeNull();
});
