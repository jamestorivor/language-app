import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WordPanel from "../src/components/transcript/WordPanel";
import InteractiveTranscript from "../src/components/transcript/InteractiveTranscript";
import * as japaneseApi from "../src/api/japanese";
import * as studyApi from "../src/api/study";
import type { TokenGroup } from "../src/contracts/japanese";

vi.mock("../src/api/japanese", () => ({ fetchJapaneseTokenGroups: vi.fn(), updateWordFamiliarity: vi.fn() }));
vi.mock("../src/api/study", () => ({ getStudyCards: vi.fn(), addStudyCard: vi.fn() }));

const word: TokenGroup = {
  word_id: 7, text: "猫", lookup_form: "猫", familiarity_score: 0,
  senses: [{ glosses: ["cat"], pos: [], stagk: [], stagr: [], s_inf: [] }],
  start_idx: 0, end_idx: 1, tokens: [], display: true,
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
  vi.mocked(japaneseApi.fetchJapaneseTokenGroups).mockResolvedValue([word]);
  vi.mocked(studyApi.getStudyCards).mockResolvedValue([]);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("study action in word popup", () => {
  it("opens a focused second page without enrolling until the final action", async () => {
    const user = userEvent.setup();
    const onAdd = vi.fn();
    const anchor = document.createElement("button");
    document.body.appendChild(anchor);
    const { unmount } = render(<WordPanel word={word} anchor={anchor} saving={false} onClose={vi.fn()} onChange={vi.fn()}
      sentence="猫がいます。" onAddToStudy={onAdd} isStudied={() => false} />);
    const panel = screen.getByRole("region", { name: "Word details" });
    expect(within(panel).getByText("cat")).toBeTruthy();
    const wontLearn = within(panel).getByText("Won’t learn");
    const addButton = within(panel).getByRole("button", { name: "Add to Study" });
    expect(wontLearn.closest(".rating-scale-actions")).toBe(addButton.parentElement);
    expect(within(panel).queryByRole("textbox", { name: "Sentence to study" })).toBeNull();
    expect(onAdd).not.toHaveBeenCalled();

    await user.click(within(panel).getByRole("button", { name: "Add to Study" }));
    expect(within(panel).getByRole("textbox", { name: "Sentence to study" })).toHaveProperty("value", "猫がいます。");
    expect(within(panel).queryByText("cat")).toBeNull();
    expect(within(panel).queryByText("Won’t learn")).toBeNull();
    expect(onAdd).not.toHaveBeenCalled();

    await user.click(within(panel).getByRole("button", { name: /Back/ }));
    expect(within(panel).getByText("cat")).toBeTruthy();
    expect(within(panel).queryByRole("textbox", { name: "Sentence to study" })).toBeNull();
    expect(onAdd).not.toHaveBeenCalled();

    await user.click(within(panel).getByRole("button", { name: "Add to Study" }));
    await user.click(within(panel).getByRole("button", { name: "Add to Study" }));
    expect(onAdd).toHaveBeenCalledOnce();
    expect(onAdd).toHaveBeenCalledWith("猫がいます。");
    unmount();
    anchor.remove();
  });

  it("offers Add to Study only when opened from the transcript, not the vocabulary summary", async () => {
    const user = userEvent.setup();
    const { container } = render(<InteractiveTranscript text="猫がいます。" language="ja" segmentId={3} />);
    const summary = await screen.findByRole("region", { name: "Words in this segment" });
    const summaryWord = await within(summary).findByRole("button", { name: "猫" });
    await user.click(summaryWord);
    let panel = screen.getByRole("region", { name: "Word details" });
    expect(within(panel).getByText("cat")).toBeTruthy();
    expect(within(panel).getByText("Won’t learn")).toBeTruthy();
    expect(within(panel).queryByRole("button", { name: "Add to Study" })).toBeNull();
    expect(within(panel).queryByRole("textbox", { name: "Sentence to study" })).toBeNull();
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
    await user.click(within(panel).getByRole("button", { name: "Close word details" }));

    const transcriptWord = container.querySelector<HTMLButtonElement>(".transcript-text button.transcript-word")!;
    expect(transcriptWord).toBeTruthy();
    await user.click(transcriptWord);
    panel = screen.getByRole("region", { name: "Word details" });
    expect(within(panel).getByRole("button", { name: "Add to Study" })).toBeTruthy();
    expect(within(panel).queryByRole("textbox", { name: "Sentence to study" })).toBeNull();
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
  });

  it("submits the edited transcript sentence only when the user confirms", async () => {
    const user = userEvent.setup();
    vi.mocked(studyApi.addStudyCard).mockResolvedValue({ id: 1, word_id: 7, sentence: "猫が", sentence_start: 0, sentence_end: 2 } as never);
    const { container } = render(<InteractiveTranscript text="猫がいます。" language="ja" segmentId={3} />);
    await screen.findByRole("region", { name: "Words in this segment" });
    await within(screen.getByRole("region", { name: "Words in this segment" })).findByRole("button", { name: "猫" });
    const transcriptWord = container.querySelector<HTMLButtonElement>(".transcript-text button.transcript-word")!;
    await user.click(transcriptWord);
    await user.click(screen.getByRole("button", { name: "Add to Study" }));
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
    const sentence = screen.getByRole("textbox", { name: "Sentence to study" });
    await user.clear(sentence);
    await user.type(sentence, "猫が");
    await user.click(screen.getByRole("button", { name: "Add to Study" }));
    expect(studyApi.addStudyCard).toHaveBeenCalledOnce();
    expect(studyApi.addStudyCard).toHaveBeenCalledWith(expect.objectContaining({
      word_id: 7, segment_id: 3, sentence: "猫が", sentence_start: 0, sentence_end: 2,
      target_start: 0, target_end: 1, target_text: "猫",
    }));
  });
});

it("allows an English transcript word to be added with its sentence", async () => {
  const user = userEvent.setup();
  const englishWord = { ...word, text: "cat", lookup_form: "cat", start_idx: 2, end_idx: 5 };
  vi.mocked(japaneseApi.fetchJapaneseTokenGroups).mockResolvedValue([englishWord]);
  vi.mocked(studyApi.addStudyCard).mockResolvedValue({ id: -1, language: "en", word_id: 7, sentence: "A cat sleeps.", sentence_start: 0, sentence_end: 13 } as never);
  const { container } = render(<InteractiveTranscript text="A cat sleeps." language="en" segmentId={3} />);
  await screen.findByRole("region", { name: "Words in this segment" });
  const transcriptWord = container.querySelector<HTMLButtonElement>(".transcript-text button.transcript-word")!;
  await user.click(transcriptWord);
  await user.click(screen.getByRole("button", { name: "Add to Study" }));
  expect(screen.getByRole("textbox", { name: "Sentence to study" })).toHaveProperty("value", "A cat sleeps.");
  await user.click(screen.getByRole("button", { name: "Add to Study" }));
  expect(studyApi.addStudyCard).toHaveBeenCalledWith(expect.objectContaining({
    word_id: 7, segment_id: 3, sentence: "A cat sleeps.", target_start: 2, target_end: 5, target_text: "cat",
  }));
});
