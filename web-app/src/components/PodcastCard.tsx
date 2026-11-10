import { Link } from "react-router";
import type { EpisodeResponse } from "../contracts/podcast";

export default function PodcastCard({ episode, onDelete, deleting, deleteDisabled }: {
  episode: EpisodeResponse;
  onDelete: (episode: EpisodeResponse) => void;
  deleting: boolean;
  deleteDisabled: boolean;
}) {
  return (
    <div className="flex h-full flex-col rounded-2xl border border-stone-200 bg-white shadow-sm transition hover:border-emerald-700/40 hover:shadow-md">
      <Link
        to={`/podcasts/${episode.id}`}
        state={{ episode }}
        className="group flex flex-1 flex-col rounded-t-2xl px-6 pt-6 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
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
      <div className="px-6 pb-5 pt-4">
        <button type="button" onClick={() => onDelete(episode)} disabled={deleteDisabled}
          aria-label={`Delete ${episode.title}`}
          className="rounded text-sm font-medium text-red-700 hover:text-red-900 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700">
          {deleting ? "Deleting…" : "Delete"}
        </button>
      </div>
    </div>
  );
}
