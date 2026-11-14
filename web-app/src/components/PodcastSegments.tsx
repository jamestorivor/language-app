import { Link, useParams, useLocation, useNavigate } from "react-router";
import { useEffect, useState, type FormEvent } from "react";
import type {
  EpisodeResponse,
  ListSegmentResponse,
  PodcastLanguage,
  EpisodeVocabulary,
} from "../contracts/podcast";
import { deleteEpisode, getEpisodeById, getSegments, getVocabulary, updateEpisode } from "../api/podcast";
import { formatTime } from "../utils/formatTime";
import VocabularySummary from "./VocabularySummary";
import TranscriptFileInput from "./TranscriptFileInput";
import { readTranscriptFile } from "../utils/transcriptFile";
import parsePodcastLink from "../utils/urlParser";
import { getLastWatched } from "../utils/lastWatched";

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
  const navigate = useNavigate();
  const [episode, setEpisode] = useState<EpisodeResponse | undefined>(
    (location.state as { episode?: EpisodeResponse } | null)?.episode,
  );
  const [segements, setSegements] = useState<ListSegmentResponse>([]);
  const [vocabulary, setVocabulary] = useState<EpisodeVocabulary | null>(null);
  const [vocabularyError, setVocabularyError] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [editError, setEditError] = useState("");

  async function saveDetails(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const title = String(form.get("title") ?? "").trim();
    const author = String(form.get("author") ?? "").trim();
    const language: PodcastLanguage = form.get("language") === "en" ? "en" : "ja";
    const segmentSize = String(form.get("segmentSizeMinutes") ?? "").trim();
    const chunk_interval = segmentSize ? Number(segmentSize) * 60 : undefined;
    if (!title || !author) {
      setEditError("Please enter a title and author.");
      return;
    }
    if (chunk_interval !== undefined && (!Number.isFinite(chunk_interval) || chunk_interval <= 0)) {
      setEditError("Enter a segment length greater than zero.");
      return;
    }
    setSaving(true);
    setEditError("");
    try {
      const transcript = await readTranscriptFile(form.get("transcript"));
      const external_transcript = transcript?.text;
      const external_transcript_format = transcript?.format;
      const refresh_youtube_transcript = form.get("refreshYoutubeTranscript") === "on";
      setEpisode(await updateEpisode(id, { title, author, language, external_transcript, external_transcript_format, chunk_interval, refresh_youtube_transcript }));
      if (external_transcript !== undefined || chunk_interval !== undefined) setSegements(await getSegments(id));
      setEditing(false);
      void getVocabulary(id).then((result) => { setVocabulary(result); setVocabularyError(false); }).catch(() => setVocabularyError(true));
    } catch (error) {
      setEditError(error instanceof Error ? error.message : "Could not save changes. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!episode || !window.confirm(`Delete “${episode.title}” and its segments and transcripts? This cannot be undone.`)) return;
    setEditError("");
    setDeleting(true);
    try {
      await deleteEpisode(episode.id);
      navigate(`/podcasts?language=${episode.language}`, { replace: true });
    } catch {
      setEditError("Could not delete the podcast. Please try again.");
      setDeleting(false);
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
    void getVocabulary(id).then(setVocabulary).catch(() => setVocabularyError(true));
  }, [podcastId]);
  const lastWatched = episode ? getLastWatched(episode) : null;
  const lastWatchedSegment = lastWatched === null ? undefined : segements.find(
    (segment) => segment.start_time <= lastWatched && lastWatched < segment.end_time,
  );
  return (
    <div className="mx-auto max-w-4xl">
      <Link
        to={`/podcasts?language=${episode?.language ?? "ja"}`}
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
              <div>
                <label htmlFor="edit-language" className="block text-sm font-semibold text-stone-700">Podcast language</label>
                <select id="edit-language" name="language" defaultValue={episode.language} className="mt-2 w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-stone-900 focus:outline-2 focus:outline-emerald-800">
                  <option value="ja">Japanese</option>
                  <option value="en">English</option>
                </select>
                <p className="mt-2 text-sm text-stone-500">Changing the language changes how existing transcripts are read; it does not replace their text.</p>
              </div>
              <div>
                <label htmlFor="edit-segment-size" className="block text-sm font-semibold text-stone-700">New segment length (minutes)</label>
                <input id="edit-segment-size" name="segmentSizeMinutes" type="number" min="0.01" step="any" placeholder="Leave blank to keep current segments" aria-describedby="edit-segment-size-help" className="mt-2 w-full rounded-lg border border-stone-300 px-3 py-2 text-stone-900 focus:outline-2 focus:outline-emerald-800" />
                <p id="edit-segment-size-help" className="mt-2 text-sm text-stone-500">Changing the length rebuilds every segment and replaces its transcript and vocabulary baseline. Upload a timestamped transcript below{parsePodcastLink(episode.audio_location)?.provider === "youtube" ? " or use YouTube captions" : ""}. Existing segment links may change or stop working.</p>
              </div>
              <TranscriptFileInput id="edit-transcript" />
              <p className="text-sm text-stone-500">Replacing the transcript or changing the language starts a new vocabulary baseline.</p>
              {parsePodcastLink(episode.audio_location)?.provider === "youtube" && (
                <label className="flex items-start gap-2 text-sm text-stone-700">
                  <input type="checkbox" name="refreshYoutubeTranscript" className="mt-1" />
                  <span>Use current YouTube captions when changing segment length (replaces existing transcripts).</span>
                </label>
              )}
              {editError && <p role="alert" className="text-sm text-red-700">{editError}</p>}
              <div className="flex flex-wrap gap-3">
                <button type="submit" disabled={saving || deleting} className="rounded-lg bg-emerald-900 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{saving ? "Saving…" : "Save changes"}</button>
                <button type="button" disabled={saving || deleting} onClick={() => setEditing(false)} className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50 disabled:opacity-50">Cancel</button>
              </div>
              <div className="border-t border-stone-200 pt-4">
                <button type="button" disabled={saving || deleting} onClick={handleDelete}
                  className="rounded text-sm font-semibold text-red-700 hover:text-red-900 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700">
                  {deleting ? "Deleting…" : "Delete podcast"}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
      <div className="mx-auto mt-8 max-w-2xl">
        {vocabularyError ? <p role="alert" className="text-sm text-red-700">Could not load the vocabulary estimate.</p> : vocabulary ? <VocabularySummary comparison={vocabulary.episode} baselineAt={vocabulary.baseline_at} addedAt={vocabulary.added_at} segmentsWithText={vocabulary.segments_with_text} segmentCount={vocabulary.segment_count} /> : <p className="text-sm text-stone-500">Calculating vocabulary estimate…</p>}
      </div>
      <section className="mt-12 border-t border-stone-200 pt-8 sm:mt-16" aria-labelledby="segments-heading">
        <h2 id="segments-heading" className="text-xl font-semibold tracking-tight">Choose a segment</h2>
        <p className="mt-1 text-sm text-stone-500">
          Pick up anywhere to listen and read along.
        </p>
        <ul className="mt-5 grid gap-3 sm:grid-cols-2">
          {segements.map((segment, index) => (
            <li key={segment.id}>
              <Link
                state={{ segment: episode ? { ...segment, episode_title: episode.title, episode_author: episode.author, episode_language: episode.language } : segment }}
                to={`/podcasts/segments/${segment.id}`}
                className={`group flex h-full items-center gap-4 rounded-2xl border p-4 shadow-sm transition hover:border-emerald-700/40 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 sm:p-5 ${segment.id === lastWatchedSegment?.id ? "border-emerald-700 bg-emerald-50/50" : "border-stone-200 bg-white"}`}
              >
                <span aria-hidden="true" className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-sm font-bold tabular-nums text-emerald-800">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-xs font-semibold uppercase tracking-wide text-stone-500">
                    Segment <span className="sr-only">{index + 1}</span>
                  </span>
                  <span className="mt-1 block text-base font-semibold tabular-nums text-stone-900">
                    {formatTime(segment.start_time)} – {formatTime(segment.end_time)}
                  </span>
                  {vocabulary?.segments[String(segment.id)]?.current && <VocabularySummary compact comparison={vocabulary.segments[String(segment.id)]} />}
                  {segment.id === lastWatchedSegment?.id && (
                    <span className="mt-2 inline-block rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-900">Last watched</span>
                  )}
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
