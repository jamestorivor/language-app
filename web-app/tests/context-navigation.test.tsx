import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import type { StudySource } from "../src/api/study";
import { verifiedCueTime, verifiedTranscriptContext } from "../src/utils/contextNavigation";
import InteractiveTranscript from "../src/components/transcript/InteractiveTranscript";
import YouTubeSegmentPlayer from "../src/components/YouTubeSegmentPlayer";
import PodcastDetail from "../src/components/PodcastDetail";
import * as podcastApi from "../src/api/podcast";
import * as japaneseApi from "../src/api/japanese";
import * as studyApi from "../src/api/study";

vi.mock("../src/api/japanese", () => ({ fetchJapaneseTokenGroups: vi.fn(), updateWordFamiliarity: vi.fn() }));
vi.mock("../src/api/study", () => ({ getStudyCards: vi.fn(), getStudySources: vi.fn(), addStudyCard: vi.fn() }));
vi.mock("../src/api/podcast", () => ({ getSegmentById: vi.fn(), getEpisodeById: vi.fn(), getVocabulary: vi.fn() }));

const text = "😀猫です。猫がいます。";
const source: StudySource = {
  id: 10, card_id: 5, word_id: 7, episode_id: 2, episode_title: "Episode", segment_id: 3,
  sentence: "猫がいます。", target_text: "猫", target_start: 0, target_end: 1, sentence_start: 5, sentence_end: 11,
  transcript_start: 5, transcript_end: 11, start_ms: 12345, end_ms: 15500, timing: "cue", source_status: "available",
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
  vi.mocked(studyApi.getStudyCards).mockResolvedValue([]);
  vi.mocked(japaneseApi.fetchJapaneseTokenGroups).mockResolvedValue([]);
});
afterEach(() => { cleanup(); delete window.YT; vi.useRealTimers(); vi.unstubAllGlobals(); });

describe("context validation", () => {
  it("highlights the selected occurrence using Unicode offsets, never another matching word", () => {
    expect(verifiedTranscriptContext(text, source, 3)).toEqual({ sentenceStart: 5, sentenceEnd: 11, targetStart: 5, targetEnd: 6 });
    expect(verifiedTranscriptContext(text, { ...source, target_start: 1 }, 3)).toBeNull();
    expect(verifiedTranscriptContext("😀猫です。犬がいます。", source, 3)).toBeNull();
    expect(verifiedTranscriptContext(text, { ...source, source_status: "changed" }, 3)).toBeNull();
    expect(verifiedTranscriptContext(text, source, 4)).toBeNull();
  });

  it("uses a verified cue timestamp, never a segment boundary as a guess", () => {
    expect(verifiedCueTime(source, 0, 60)).toEqual({ startMs: 12345, endMs: 15500 });
    expect(verifiedCueTime({ ...source, timing: "unknown", start_ms: null }, 0, 60)).toBeNull();
    expect(verifiedCueTime({ ...source, source_status: "changed" }, 0, 60)).toBeNull();
    expect(verifiedCueTime({ ...source, start_ms: 70000 }, 0, 60)).toBeNull();
    expect(verifiedCueTime({ ...source, start_ms: 59000, end_ms: 61500 }, 0, 60)).toEqual({ startMs: 59000, endMs: 61500 });
  });
});

describe("interactive transcript context", () => {
  it("marks only the verified occurrence while word inspection does not enroll anything", async () => {
    const tokens = [1, 5].map((index) => ({
      word_id: 7, text: "猫", lookup_form: "猫", familiarity_score: 0, senses: [],
      start_idx: index, end_idx: index + 1, tokens: [], display: true,
    }));
    vi.mocked(japaneseApi.fetchJapaneseTokenGroups).mockResolvedValue(tokens);
    const { container } = render(<InteractiveTranscript text={text} language="ja" segmentId={3} context={verifiedTranscriptContext(text, source, 3)} />);
    await waitFor(() => expect(container.querySelectorAll("button.transcript-word")).toHaveLength(3));
    const transcript = container.querySelector(".transcript-text")!;
    const marks = transcript.querySelectorAll("mark[data-context-target]");
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe("猫");
    const buttons = transcript.querySelectorAll("button.transcript-word");
    expect(buttons[0].querySelector("mark")).toBeNull();
    expect(buttons[1].querySelector("mark")).not.toBeNull();
    fireEvent.click(buttons[1]);
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
  });
});

describe("YouTube context playback", () => {
  it("cues the exact timestamp without autoplay and plays/replays only on request", async () => {
    const cue = vi.fn(), seek = vi.fn(), play = vi.fn(), pause = vi.fn();
    let currentTime = 12.345;
    class FakePlayer {
      cueVideoById = cue; seekTo = seek; playVideo = play; pauseVideo = pause;
      destroy = vi.fn(); getCurrentTime = () => currentTime; getPlayerState = () => 1;
      constructor(_element: HTMLElement, options: { events: { onReady: (event: { target: FakePlayer }) => void } }) {
        queueMicrotask(() => options.events.onReady({ target: this }));
      }
    }
    window.YT = { Player: FakePlayer } as never;
    render(<YouTubeSegmentPlayer videoId="video" startTime={0} endTime={60} title="Episode" isPinned={false} onPlaybackStart={() => {}} contextTime={{ startMs: 12345, endMs: 15500 }} />);
    await waitFor(() => expect(cue).toHaveBeenCalled());
    expect(cue).toHaveBeenCalledWith({ videoId: "video", startSeconds: 12.345, endSeconds: 60 });
    expect(play).not.toHaveBeenCalled();
    const button = screen.getByRole("button", { name: "Play or replay caption" });
    fireEvent.click(button);
    currentTime = 15.5;
    await waitFor(() => expect(pause).toHaveBeenCalledTimes(1));
    currentTime = 12.345;
    fireEvent.click(button);
    expect(seek).toHaveBeenNthCalledWith(1, 12.345, true);
    expect(seek).toHaveBeenCalledTimes(2);
    expect(play).toHaveBeenCalledTimes(2);
    const mobileControls = screen.getByRole("region", { name: "Playback controls" });
    fireEvent.click(within(mobileControls).getByRole("button", { name: "Forward 10 seconds" }));
    expect(seek).toHaveBeenLastCalledWith(22.345, true);
  });

  it("plays a caption that crosses a segment boundary through its recorded end", async () => {
    const cue = vi.fn(), seek = vi.fn(), play = vi.fn(), pause = vi.fn();
    let currentTime = 59;
    class FakePlayer {
      cueVideoById = cue; seekTo = seek; playVideo = play; pauseVideo = pause;
      destroy = vi.fn(); getCurrentTime = () => currentTime; getPlayerState = () => 1;
      constructor(_element: HTMLElement, options: { events: { onReady: (event: { target: FakePlayer }) => void } }) {
        queueMicrotask(() => options.events.onReady({ target: this }));
      }
    }
    window.YT = { Player: FakePlayer } as never;
    render(<YouTubeSegmentPlayer videoId="video" startTime={0} endTime={60} title="Episode" isPinned={false} onPlaybackStart={() => {}} contextTime={{ startMs: 59000, endMs: 61500 }} />);
    await waitFor(() => expect(cue).toHaveBeenCalledWith({ videoId: "video", startSeconds: 59, endSeconds: 61.5 }));
    fireEvent.click(screen.getByRole("button", { name: "Play or replay caption" }));
    currentTime = 60.2;
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 240)); });
    expect(pause).not.toHaveBeenCalled();
    currentTime = 61.5;
    await waitFor(() => expect(pause).toHaveBeenCalled());
    expect(seek).toHaveBeenCalledWith(59, true);
    expect(play).toHaveBeenCalledTimes(1);
  });
});

describe("source navigation", () => {
  it("loads the saved source and cues its timestamp without enrolling or reviewing", async () => {
    vi.mocked(studyApi.getStudySources).mockResolvedValue([source]);
    vi.mocked(podcastApi.getSegmentById).mockResolvedValue({ id: 3, user_id: 1, podcast_id: 2, start_time: 0, end_time: 60, episode_title: "Episode", episode_author: "Author", episode_language: "ja", transcript: { id: 1, podcast_chunk_id: 3, text } });
    vi.mocked(podcastApi.getEpisodeById).mockResolvedValue({ id: 2, user_id: 1, title: "Episode", author: "Author", duration: 60, language: "ja", added_at: null, audio_location: "https://example.test/unsupported" });
    vi.mocked(podcastApi.getVocabulary).mockResolvedValue({ added_at: null, baseline_at: null, segments_with_text: 1, segment_count: 1, episode: null, segments: {} });
    const { container } = render(<MemoryRouter initialEntries={["/podcasts/segments/3?study_card=5&context=10"]}><Routes><Route path="/podcasts/segments/:segmentId" element={<PodcastDetail />} /></Routes></MemoryRouter>);
    expect(await screen.findByText(/Saved sentence found/)).toBeTruthy();
    expect(studyApi.getStudySources).toHaveBeenCalledWith(5);
    await waitFor(() => expect(container.querySelector("mark[data-context-target]")?.textContent).toBe("猫"));
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
  });

  it("opens the source for an English card", async () => {
    vi.mocked(studyApi.getStudySources).mockResolvedValue([{ ...source, card_id: -5 }]);
    vi.mocked(podcastApi.getSegmentById).mockResolvedValue({ id: 3, user_id: 1, podcast_id: 2, start_time: 0, end_time: 60, episode_title: "Episode", episode_author: "Author", episode_language: "en", transcript: { id: 1, podcast_chunk_id: 3, text } });
    vi.mocked(podcastApi.getEpisodeById).mockResolvedValue({ id: 2, user_id: 1, title: "Episode", author: "Author", duration: 60, language: "en", added_at: null, audio_location: "https://example.test/unsupported" });
    vi.mocked(podcastApi.getVocabulary).mockResolvedValue({ added_at: null, baseline_at: null, segments_with_text: 1, segment_count: 1, episode: null, segments: {} });
    render(<MemoryRouter initialEntries={["/podcasts/segments/3?study_card=-5&context=10"]}><Routes><Route path="/podcasts/segments/:segmentId" element={<PodcastDetail />} /></Routes></MemoryRouter>);
    expect(await screen.findByText(/Saved sentence found/)).toBeTruthy();
    expect(studyApi.getStudySources).toHaveBeenCalledWith(-5);
  });

  it("warns instead of highlighting or seeking after a transcript edit", async () => {
    vi.mocked(studyApi.getStudySources).mockResolvedValue([{ ...source, source_status: "changed" }]);
    vi.mocked(podcastApi.getSegmentById).mockResolvedValue({ id: 3, user_id: 1, podcast_id: 2, start_time: 0, end_time: 60, episode_title: "Episode", episode_author: "Author", episode_language: "ja", transcript: { id: 1, podcast_chunk_id: 3, text: "😀猫です。犬がいます。" } });
    vi.mocked(podcastApi.getEpisodeById).mockResolvedValue({ id: 2, user_id: 1, title: "Episode", author: "Author", duration: 60, language: "ja", added_at: null, audio_location: "https://example.test/unsupported" });
    vi.mocked(podcastApi.getVocabulary).mockResolvedValue({ added_at: null, baseline_at: null, segments_with_text: 1, segment_count: 1, episode: null, segments: {} });
    const { container } = render(<MemoryRouter initialEntries={["/podcasts/segments/3?study_card=5&context=10"]}><Routes><Route path="/podcasts/segments/:segmentId" element={<PodcastDetail />} /></Routes></MemoryRouter>);
    expect(await screen.findByText(/transcript has changed/)).toBeTruthy();
    expect(container.querySelector("mark[data-context-target]")).toBeNull();
    expect(screen.queryByRole("button", { name: /replay caption/ })).toBeNull();
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
  });

  it("follows a source that has moved to a rebuilt segment", async () => {
    vi.mocked(studyApi.getStudySources).mockResolvedValue([{ ...source, segment_id: 4 }]);
    vi.mocked(podcastApi.getSegmentById).mockImplementation(async (id) => ({ id, user_id: 1, podcast_id: 2, start_time: 0, end_time: 60, episode_title: "Episode", episode_author: "Author", episode_language: "ja", transcript: { id, podcast_chunk_id: id, text } }));
    vi.mocked(podcastApi.getEpisodeById).mockResolvedValue({ id: 2, user_id: 1, title: "Episode", author: "Author", duration: 60, language: "ja", added_at: null, audio_location: "https://example.test/unsupported" });
    vi.mocked(podcastApi.getVocabulary).mockResolvedValue({ added_at: null, baseline_at: null, segments_with_text: 1, segment_count: 1, episode: null, segments: {} });
    render(<MemoryRouter initialEntries={["/podcasts/segments/3?study_card=5&context=10"]}><Routes><Route path="/podcasts/segments/:segmentId" element={<PodcastDetail />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(podcastApi.getSegmentById).toHaveBeenCalledWith(4));
    expect(await screen.findByText(/Saved sentence found/)).toBeTruthy();
    expect(studyApi.addStudyCard).not.toHaveBeenCalled();
  });
});
