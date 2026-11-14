import { useRef, useState, type SubmitEvent } from "react";
import type { CreateEpisodeRequest, PodcastLanguage } from "../contracts/podcast";
import { createEpisode } from "../api/podcast";
import { useNavigate, useSearchParams } from "react-router";
import parsePodcastLink from "../utils/urlParser";
import type { PodcastLink } from "../utils/urlParser";
import TranscriptFileInput from "./TranscriptFileInput";
import { readTranscriptFile } from "../utils/transcriptFile";
function AddPodcastCard() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [errorMessage, setErrorMessage] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const isAddingRef = useRef(false);

  async function handleAddButtonClick(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isAddingRef.current) return;
    setErrorMessage("");
    const form = new FormData(event.currentTarget);

    const url = String(form.get("url") ?? "");

    const podcastLink: PodcastLink | null = parsePodcastLink(url);
    if (podcastLink == null) {
      setErrorMessage(
        "Invalid URL, only Youtube and Spotify links are supported",
      );
      return;
    }

    const title = String(form.get("title") ?? "");
    const creator = String(form.get("creator") ?? "");
    const segmentSize = Number(form.get("segmentSizeMinutes"));

    const episodeRequest: CreateEpisodeRequest = {
      audio_location: url,
      title: title,
      author: creator,
      chunk_interval: segmentSize * 60,
      podcast_details: podcastLink,
      language: form.get("language") === "en" ? "en" : "ja",
    };

    isAddingRef.current = true;
    setIsAdding(true);
    try {
      const transcript = await readTranscriptFile(form.get("transcript"));
      episodeRequest.external_transcript = transcript?.text;
      episodeRequest.external_transcript_format = transcript?.format;
      const episode = await createEpisode(episodeRequest);
      const episodeId = episode.id;

      navigate(`/podcasts/${episodeId}`, { state: { episode } });
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Something went wrong",
      );
    } finally {
      isAddingRef.current = false;
      setIsAdding(false);
    }
  }

  return (
    <>
      <section className="mt-8 w-full max-w-2xl rounded-2xl border border-stone-200 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-xl font-semibold tracking-tight text-stone-950">
          Podcast details
        </h2>
        <p className="mt-2 text-sm leading-6 text-stone-500">
          Enter a podcast or episode link to get started.
        </p>

        <form className="mt-6 space-y-5" onSubmit={handleAddButtonClick}>
          <div>
            <label htmlFor="podcast-language" className="block text-sm font-medium text-stone-700">Podcast language</label>
            <select id="podcast-language" name="language" defaultValue={(searchParams.get("language") === "en" ? "en" : "ja") satisfies PodcastLanguage}
              className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-sm text-stone-900 focus:border-stone-500 focus:outline-none focus:ring-2 focus:ring-stone-200">
              <option value="ja">Japanese</option>
              <option value="en">English</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="podcast-url"
              className="block text-sm font-medium text-stone-700"
            >
              Podcast link <span className="text-red-600">*</span>
            </label>
            <input
              id="podcast-url"
              name="url"
              type="url"
              required
              placeholder="https://..."
              aria-describedby="podcast-url-help"
              onChange={() => setErrorMessage("")}
              className="mt-2 block w-full rounded-lg border border-stone-300 px-3 py-2.5 text-sm text-stone-900 placeholder:text-stone-400 focus:border-stone-500 focus:outline-none focus:ring-2 focus:ring-stone-200"
            />
            <p id="podcast-url-help" className="mt-2 text-sm text-stone-500">
              Enter a podcast or episode link.
            </p>
          </div>

          <div>
            <label
              htmlFor="podcast-title"
              className="block text-sm font-medium text-stone-700"
            >
              Title{" "}
              <span className="font-normal text-stone-400">(required)</span>
            </label>
            <input
              id="podcast-title"
              name="title"
              type="text"
              required
              placeholder="Give it a name"
              className="mt-2 block w-full rounded-lg border border-stone-300 px-3 py-2.5 text-sm text-stone-900 placeholder:text-stone-400 focus:border-stone-500 focus:outline-none focus:ring-2 focus:ring-stone-200"
            />
          </div>

          <div>
            <label
              htmlFor="podcast-creator"
              className="block text-sm font-medium text-stone-700"
            >
              Creator name{" "}
              <span className="font-normal text-stone-400">(required)</span>
            </label>
            <input
              id="podcast-creator"
              name="creator"
              type="text"
              required
              placeholder="Podcast creator"
              className="mt-2 block w-full rounded-lg border border-stone-300 px-3 py-2.5 text-sm text-stone-900 placeholder:text-stone-400 focus:border-stone-500 focus:outline-none focus:ring-2 focus:ring-stone-200"
            />
          </div>

          <div>
            <label
              htmlFor="segment-size"
              className="block text-sm font-medium text-stone-700"
            >
              Segment size (minutes)
            </label>
            <input
              id="segment-size"
              name="segmentSizeMinutes"
              type="number"
              min="1"
              step="1"
              defaultValue="5"
              required
              aria-describedby="segment-size-help"
              className="mt-2 block w-full rounded-lg border border-stone-300 px-3 py-2.5 text-sm text-stone-900 focus:border-stone-500 focus:outline-none focus:ring-2 focus:ring-stone-200"
            />
            <p id="segment-size-help" className="mt-2 text-sm text-stone-500">
              Choose the length of each segment in minutes.
            </p>
          </div>

          <TranscriptFileInput id="add-transcript" />
          {errorMessage && <p role="alert" className="text-sm text-red-600">{errorMessage}</p>}

          <div>
            <button
              type="submit"
              disabled={isAdding}
              className="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-emerald-900 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isAdding && (
                <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white motion-reduce:animate-none" />
              )}
              <span role="status">{isAdding ? "Adding podcast…" : "Add podcast"}</span>
            </button>
          </div>
        </form>
      </section>
    </>
  );
}

export default AddPodcastCard;
