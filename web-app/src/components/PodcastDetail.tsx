import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router";
import type { EpisodeResponse, SegmentResponse, EpisodeVocabulary } from "../contracts/podcast";
import { getEpisodeById, getSegmentById, getVocabulary } from "../api/podcast";
import { formatTime } from "../utils/formatTime";
import parsePodcastLink from "../utils/urlParser";
import VocabularySummary from "./VocabularySummary";
import InteractiveTranscript from "./transcript/InteractiveTranscript";
import YouTubeSegmentPlayer from "./YouTubeSegmentPlayer";
import { saveLastWatched } from "../utils/lastWatched";

const PINNED_VIDEO_SIZES = [
  { width: "20rem", percent: "65%" },
  { width: "36rem", percent: "80%" },
  { width: "56rem", percent: "100%" },
];

export default function PodcastDetail() {
  const { segmentId } = useParams();
  return <SegmentDetail key={segmentId} segmentId={segmentId} />;
}

function SegmentDetail({ segmentId }: { segmentId: string | undefined }) {
  const location = useLocation();
  const id = Number(segmentId);
  const [segment, setSegment] = useState<SegmentResponse | undefined>(
    (location.state as { segment?: SegmentResponse } | null)?.segment?.id === id
      ? (location.state as { segment: SegmentResponse }).segment
      : undefined,
  );
  const [loadError, setLoadError] = useState<string | null>(null);
  const [vocabulary, setVocabulary] = useState<EpisodeVocabulary | null>(null);
  const [vocabularyError, setVocabularyError] = useState(false);
  const [isPinned, setIsPinned] = useState(false);
  const [pinnedSize, setPinnedSize] = useState(1);

  useEffect(() => {
    let cancelled = false;
    async function loadSegment(segmentId: number) {
      try {
        const result = await getSegmentById(segmentId);
        if (!cancelled) setSegment(result);
      } catch {
        if (!cancelled) setLoadError("Could not load this segment.");
      }
    }
    void loadSegment(id);
    return () => { cancelled = true; };
  }, [id]);

  const refreshVocabulary = useCallback(() => {
    if (!segment) return;
    void getVocabulary(segment.podcast_id).then((result) => { setVocabulary(result); setVocabularyError(false); }).catch(() => setVocabularyError(true));
  }, [segment]);

  useEffect(() => { refreshVocabulary(); }, [refreshVocabulary]);

  if (loadError) return <p role="alert">{loadError}</p>;
  if (!segment) return <>Loading...</>;
  else
    return (
      <div className={isPinned ? "pb-0" : "pb-36 sm:pb-0"}>
        <Link
          to={`/podcasts/${segment.podcast_id}`}
          className="text-sm font-semibold text-emerald-800 hover:text-emerald-950 hover:underline"
        >
          ← All segments
        </Link>
        <p className="mt-7 text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">Listening practice</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-stone-950 sm:text-4xl">{segment.episode_title}</h1>
        <p className="mt-3 text-base text-stone-600">{segment.episode_author}</p>
        <p className="mt-4 inline-block rounded-full bg-stone-200/70 px-3 py-1 text-sm font-medium tabular-nums text-stone-700">
          {formatTime(segment.start_time)} – {formatTime(segment.end_time)}
        </p>
        <div className="mt-8 flex flex-col gap-6">
          <section
            className={`mx-auto w-full rounded-2xl border border-stone-200 bg-white shadow-sm ${
              isPinned
                ? "sticky top-[env(safe-area-inset-top)] z-30 p-2 shadow-lg"
                : "max-w-xl p-4 sm:p-6"
            }`}
            style={isPinned ? { width: `min(${PINNED_VIDEO_SIZES[pinnedSize].width}, ${PINNED_VIDEO_SIZES[pinnedSize].percent}, calc(115.55dvh - 6.22rem))` } : undefined}
          >
            <SegmentPlayer segment={segment} isPinned={isPinned} pinnedSize={pinnedSize} onChangePinnedSize={setPinnedSize} onTogglePin={() => setIsPinned((pinned) => !pinned)} />
          </section>
          {vocabularyError ? <p role="alert" className="text-sm text-red-700">Could not load the vocabulary estimate.</p> : vocabulary ? <VocabularySummary comparison={vocabulary.segments[String(segment.id)]} baselineAt={vocabulary.baseline_at} addedAt={vocabulary.added_at} /> : <p className="text-sm text-stone-500">Calculating vocabulary estimate…</p>}
          <InteractiveTranscript onRatingSaved={refreshVocabulary} key={`${segment.id}-${segment.episode_language}`} text={segment.transcript?.text ?? ""} language={segment.episode_language} />
        </div>
      </div>
    );
}

function SegmentPlayer({ segment, isPinned, pinnedSize, onChangePinnedSize, onTogglePin }: { segment: SegmentResponse; isPinned: boolean; pinnedSize: number; onChangePinnedSize: (size: number) => void; onTogglePin: () => void }) {
  const [episode, setEpisode] = useState<EpisodeResponse>();
  const [error, setError] = useState(false);
  const handlePlaybackStart = useCallback(() => {
    if (episode) saveLastWatched(episode, segment.start_time);
  }, [episode, segment.start_time]);

  useEffect(() => {
    let cancelled = false;
    void getEpisodeById(segment.podcast_id).then((result) => {
      if (!cancelled) setEpisode(result);
    }).catch(() => {
      if (!cancelled) setError(true);
    });
    return () => { cancelled = true; };
  }, [segment.podcast_id]);

  if (error) return <><h2 className="text-lg font-semibold tracking-tight">Player</h2><p role="alert" className="mt-3 text-sm text-red-700">Could not load the episode player.</p></>;
  if (!episode) return <><h2 className="text-lg font-semibold tracking-tight">Player</h2><p className="mt-3 text-sm text-stone-500">Loading player...</p></>;

  const link = parsePodcastLink(episode.audio_location);
  if (link?.provider !== "youtube") {
    return <><h2 className="text-lg font-semibold tracking-tight">Player</h2><p className="mt-3 text-sm text-stone-500">Playback is currently available for YouTube episodes only.</p></>;
  }

  return (
    <>
      {isPinned ? (
        <div className="flex items-center justify-end gap-1">
          <button type="button" aria-label="Make video smaller" disabled={pinnedSize === 0} onClick={() => onChangePinnedSize(pinnedSize - 1)} className="h-9 min-w-9 rounded-lg text-lg font-semibold text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-40">−</button>
          <button type="button" aria-label="Make video larger" disabled={pinnedSize === PINNED_VIDEO_SIZES.length - 1} onClick={() => onChangePinnedSize(pinnedSize + 1)} className="h-9 min-w-9 rounded-lg text-lg font-semibold text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-40">+</button>
          <button type="button" onClick={onTogglePin} className="rounded-lg px-3 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">Unpin video</button>
        </div>
      ) : (
        <div className="flex min-w-0 items-center justify-between gap-3">
          <h2 className="text-lg font-semibold tracking-tight">Player</h2>
          <button type="button" onClick={onTogglePin} className="shrink-0 rounded-lg border border-stone-300 px-3 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">Pin to top</button>
        </div>
      )}
      <YouTubeSegmentPlayer
        videoId={link.id}
        startTime={segment.start_time}
        endTime={segment.end_time}
        title={`${segment.episode_title} segment`}
        isPinned={isPinned}
        onPlaybackStart={handlePlaybackStart}
      />
    </>
  );
}
