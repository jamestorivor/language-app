import { Link } from "react-router";
import type { EpisodeResponse } from "../contracts/podcast";

export default function PodcastCard({ episode }: { episode: EpisodeResponse }) {
  return (
    <>
      <Link
        to={`/podcasts/${episode.id}`}
        state={{ episode }}
        className="group flex h-full flex-col rounded-2xl border border-stone-200 bg-white p-6 shadow-sm transition hover:border-emerald-700/40 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
      >
        {/* <p className="text-xs font-medium uppercase tracking-wide text-stone-500">
          Sample podcast
        </p> */}
        <h2 className="text-xl font-semibold leading-snug tracking-tight text-stone-950">
          {episode.title}
        </h2>
        <p className="mt-1 text-sm text-stone-500">{episode.author}</p>
        <span className="mt-auto pt-6 text-sm font-semibold text-emerald-800 group-hover:text-emerald-950">
          View podcast →
        </span>
      </Link>
    </>
  );
}
