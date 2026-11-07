import { Link, useParams, useLocation } from "react-router";
import { useEffect, useState, type FormEvent } from "react";
import type {
  EpisodeResponse,
  ListSegmentResponse,
} from "../contracts/podcast";
import { getEpisodeById, getSegments, updateEpisode } from "../api/podcast";
import { formatTime } from "../utils/formatTime";

// export const sampleApiSegments: ListSegmentResponse = [
//   {
//     id: 1,
//     user_id: 1,
//     podcast_id: 1,
//     episode_title: "Japanese listening practice",
//     episode_author: "Sample creator",
//     start_time: 0,
//     end_time: 300,
//     transcript: null,
//   },
//   {
//     id: 2,
//     user_id: 1,
//     podcast_id: 1,
//     episode_title: "Japanese listening practice",
//     episode_author: "Sample creator",
//     start_time: 300,
//     end_time: 600,
//     transcript: null,
//   },
//   {
//     id: 3,
//     user_id: 1,
//     podcast_id: 1,
//     episode_title: "Japanese listening practice",
//     episode_author: "Sample creator",
//     start_time: 600,
//     end_time: 900,
//     transcript: null,
//   },
// ];

export default function PodcastSegments() {
  const { podcastId } = useParams();
  const id = Number(podcastId);
  const location = useLocation();
  const [episode, setEpisode] = useState<EpisodeResponse | undefined>(
    (location.state as { episode?: EpisodeResponse } | null)?.episode,
  );
  const [segements, setSegements] = useState<ListSegmentResponse>([]);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState("");

  async function saveDetails(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const title = String(form.get("title") ?? "").trim();
    const author = String(form.get("author") ?? "").trim();
    if (!title || !author) {
      setEditError("Please enter a title and author.");
      return;
    }
    setSaving(true);
    setEditError("");
    try {
      setEpisode(await updateEpisode(id, { title, author }));
      setEditing(false);
    } catch {
      setEditError("Could not save changes. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    async function loadSegments() {
      if (!episode) {
        const episode = await getEpisodeById(id);
        setEpisode(episode);
      }
      const segements = await getSegments(id);
      setSegements(segements);
    }
    loadSegments();
  }, [podcastId]);
  return (
    <div className="mx-auto max-w-4xl">
      <Link
        to="/podcasts"
        className="text-sm font-semibold text-emerald-800 hover:text-emerald-950 hover:underline"
      >
        ← My podcasts
      </Link>
      {(episode || segements[0]) && (
        <div className="mx-auto mt-10 max-w-2xl text-center sm:mt-14">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">Podcast title</p>
          <h1 className="mt-3 text-3xl font-bold leading-tight tracking-tight text-stone-950 sm:text-4xl">
            {episode?.title ?? segements[0]?.episode_title}
          </h1>
          <p className="mt-4 text-base text-stone-600">
            <span className="font-medium text-stone-500">By </span>
            <span className="font-semibold text-stone-800">{episode?.author ?? segements[0]?.episode_author}</span>
          </p>
          {episode && !editing && (
            <button type="button" onClick={() => { setEditError(""); setEditing(true); }} className="mt-5 rounded-lg border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700 hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">
              Edit podcast details
            </button>
          )}
          {episode && editing && (
            <form onSubmit={saveDetails} className="mx-auto mt-6 max-w-md space-y-4 rounded-2xl border border-stone-200 bg-white p-5 text-left shadow-sm">
              <div>
                <label htmlFor="edit-title" className="block text-sm font-semibold text-stone-700">Podcast title</label>
                <input id="edit-title" name="title" defaultValue={episode.title} required className="mt-2 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 focus:outline-2 focus:outline-emerald-800" />
              </div>
              <div>
                <label htmlFor="edit-author" className="block text-sm font-semibold text-stone-700">Author</label>
                <input id="edit-author" name="author" defaultValue={episode.author} required className="mt-2 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 focus:outline-2 focus:outline-emerald-800" />
              </div>
              {editError && <p role="alert" className="text-sm text-red-700">{editError}</p>}
              <div className="flex flex-wrap gap-3">
                <button type="submit" disabled={saving} className="rounded-lg bg-emerald-900 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{saving ? "Saving…" : "Save changes"}</button>
                <button type="button" disabled={saving} onClick={() => setEditing(false)} className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50">Cancel</button>
              </div>
            </form>
          )}
        </div>
      )}
      <section className="mt-12 border-t border-stone-200 pt-8 sm:mt-16" aria-labelledby="segments-heading">
        <h2 id="segments-heading" className="text-xl font-semibold tracking-tight">Choose a segment</h2>
        <p className="mt-1 text-sm text-stone-500">
          Pick up anywhere to listen and read along.
        </p>
        <ul className="mt-5 grid gap-3 sm:grid-cols-2">
          {segements.map((segment, index) => (
            <li key={segment.id}>
              <Link
                state={{ segment: episode ? { ...segment, episode_title: episode.title, episode_author: episode.author } : segment }}
                to={`/podcasts/segments/${segment.id}`}
                className="group flex h-full items-center gap-4 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm transition hover:border-emerald-700/40 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 sm:p-5"
              >
                <span aria-hidden="true" className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-sm font-bold tabular-nums text-emerald-800">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-xs font-semibold uppercase tracking-wide text-stone-500">
                    Segment {index + 1}
                  </span>
                  <span className="mt-1 block text-base font-semibold tabular-nums text-stone-900">
                    {formatTime(segment.start_time)} – {formatTime(segment.end_time)}
                  </span>
                </span>
                <span aria-hidden="true" className="text-lg text-stone-400 transition-colors group-hover:text-emerald-800">→</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
