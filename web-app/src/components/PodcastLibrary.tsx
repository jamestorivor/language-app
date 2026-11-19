import { useLanguage } from "../i18n-context";
import { useEffect, useState } from "react";
import { getEpisodes } from "../api/podcast";
import type { EpisodeResponse } from "../contracts/podcast";
import { useStudyLanguage } from "../utils/studyLanguage";
import PodcastCard from "./PodcastCard";
import { Link, useSearchParams } from "react-router";

const sortOptions = [
  ["newest", "Date added: newest first"],
  ["oldest", "Date added: oldest first"],
  ["title-asc", "Title: A to Z"],
  ["title-desc", "Title: Z to A"],
] as const;

type SortOrder = (typeof sortOptions)[number][0];

export default function PodcastLibrary() {
  const { t, locale } = useLanguage();
  const [episodes, setEpisodes] = useState<EpisodeResponse[] | null>(null);
  const [error, setError] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const [language] = useStudyLanguage();
  const requestedSort = searchParams.get("sort");
  const sort: SortOrder = sortOptions.find(([value]) => value === requestedSort)?.[0] ?? "newest";

  function updateParam(key: string, value: string) {
    const params = new URLSearchParams(searchParams);
    params.set(key, value);
    setSearchParams(params);
  }

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

  if (error) return <p role="alert" className="mt-8 text-sm text-red-700">{t("Could not load your podcasts. Please refresh and try again.")}</p>;
  if (episodes === null) return <p role="status" className="mt-8 text-sm text-stone-500">{t("Loading your podcasts…")}</p>;
  const collator = new Intl.Collator(language, { sensitivity: "base", numeric: true });
  const filteredEpisodes = episodes.filter((episode) => episode.language === language).sort((a, b) => {
    if (sort === "title-asc" || sort === "title-desc") {
      const comparison = collator.compare(a.title, b.title);
      return (sort === "title-asc" ? comparison : -comparison) || a.id - b.id;
    }
    const aDate = a.added_at ? Date.parse(a.added_at) : NaN;
    const bDate = b.added_at ? Date.parse(b.added_at) : NaN;
    if (Number.isNaN(aDate)) return Number.isNaN(bDate) ? a.id - b.id : 1;
    if (Number.isNaN(bDate)) return -1;
    return (sort === "oldest" ? aDate - bDate : bDate - aDate) || a.id - b.id;
  });
  return (
    <>
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
      <label className="flex items-center gap-2 text-sm font-semibold text-stone-700">
        {t("Sort by")}
        <select value={sort} onChange={(event) => updateParam("sort", event.target.value)}
          className="rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">
          {sortOptions.map(([value, label]) => <option key={value} value={value}>{t(label)}</option>)}
        </select>
      </label>
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
          {locale === "ja" ? `${language === "en" ? "英語" : "日本語"}のエピソードはまだありません` : `No ${language === "en" ? "English" : "Japanese"} episodes yet`}
        </h2>
        <p className="mt-2 text-sm text-stone-500">
          {t("Add a podcast to start building your library.")}
        </p>
        <Link
          to={`/podcasts/add?language=${language}`}
          className="mt-6 inline-block rounded-xl bg-emerald-900 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
        >
          {t("Add a podcast")}
        </Link>
      </div>
      )}
    </>
  );
}
