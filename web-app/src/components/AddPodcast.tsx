import { useState, type SubmitEvent } from "react";
import type { CreateEpisodeRequest } from "../contracts/podcast";
import { createEpisode } from "../api/podcast";
import { useNavigate } from "react-router";
import parsePodcastLink from "../utils/urlParser";
import type { PodcastLink } from "../utils/urlParser";
function AddPodcastCard() {
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState("");

  async function handleAddButtonClick(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
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
    };

    try {
      const episode = await createEpisode(episodeRequest);
      const episodeId = episode.id;

      navigate(`/podcasts/${episodeId}`, { state: { episode } });
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Something went wrong",
      );
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
              aria-describedby={
                errorMessage
                  ? "podcast-url-error podcast-url-help"
                  : "podcast-url-help"
              }
              aria-invalid={Boolean(errorMessage)}
              onChange={() => setErrorMessage("")}
              className="mt-2 block w-full rounded-lg border border-stone-300 px-3 py-2.5 text-sm text-stone-900 placeholder:text-stone-400 focus:border-stone-500 focus:outline-none focus:ring-2 focus:ring-stone-200"
            />
            {errorMessage && (
              <p
                id="podcast-url-error"
                role="alert"
                className="mt-2 text-sm text-red-600"
              >
                {errorMessage}
              </p>
            )}
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

          <div>
            <button
              type="submit"
              className="cursor-pointer rounded-xl bg-emerald-900 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
            >
              Add podcast
            </button>
          </div>
        </form>
      </section>
    </>
  );
}

export default AddPodcastCard;
