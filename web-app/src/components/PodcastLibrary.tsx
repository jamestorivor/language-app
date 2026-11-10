import { useEffect, useState } from "react";
import { getEpisodes } from "../api/podcast";
import type { EpisodeResponse, PodcastLanguage } from "../contracts/podcast";
import PodcastCard from "./PodcastCard";
import { Link, useSearchParams } from "react-router";

// const fakeEpisodes: EpisodeResponse[] = [
//   {
//     id: -1,
//     user_id: 0,
//     title: "Japanese listening practice",
//     author: "Sample creator",
//     audio_location: "",
//     duration: 300,
//   },
//   {
//     id: -2,
//     user_id: 0,
//     title: "Everyday conversations",
//     author: "Sample creator",
//     audio_location: "",
//     duration: 600,
//   },
//   {
//     id: -3,
//     user_id: 0,
//     title: "A walk through Tokyo",
//     author: "Sample creator",
//     audio_location: "",
//     duration: 900,
//   },
// ];

export default function PodcastLibrary() {
  const [episodes, setEpisodes] = useState<EpisodeResponse[] | null>(null);
  const [error, setError] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const language: PodcastLanguage = searchParams.get("language") === "en" ? "en" : "ja";

  useEffect(() => {
    async function loadEpisodes() {
      try {
        setEpisodes(await getEpisodes());
      } catch {
        setError(true);
      }
    }
    loadEpisodes();
  }, []);

  if (error) return <p role="alert" className="mt-8 text-sm text-red-700">Could not load your podcasts. Please refresh and try again.</p>;
  if (episodes === null) return <p role="status" className="mt-8 text-sm text-stone-500">Loading your podcasts…</p>;
  const filteredEpisodes = episodes.filter((episode) => episode.language === language);
  return (
    <>
      <div className="mt-8 inline-flex rounded-xl bg-stone-200/70 p-1" role="group" aria-label="Podcast language">
        {([ ["ja", "Japanese"], ["en", "English"] ] as const).map(([value, label]) => (
          <button key={value} type="button" aria-pressed={language === value}
            onClick={() => setSearchParams({ language: value })}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${language === value ? "bg-white text-emerald-900 shadow-sm" : "text-stone-600 hover:text-stone-900"}`}>
            {label}
          </button>
        ))}
      </div>
      {filteredEpisodes.length > 0 ? (
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filteredEpisodes.map((episode) => (
          <PodcastCard key={episode.id} episode={episode} />
        ))}
      </div>
      ) : (
      <div className="mt-8 rounded-2xl border border-dashed border-stone-300 bg-white px-6 py-12 text-center">
        <h2 className="text-lg font-semibold text-stone-900">
          No {language === "en" ? "English" : "Japanese"} episodes yet
        </h2>
        <p className="mt-2 text-sm text-stone-500">
          Add a podcast to start building your library.
        </p>
        <Link
          to={`/podcasts/add?language=${language}`}
          className="mt-6 inline-block rounded-xl bg-emerald-900 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
        >
          Add a podcast
        </Link>
      </div>
      )}
    </>
  );
}
