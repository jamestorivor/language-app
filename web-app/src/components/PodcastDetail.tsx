import { useLanguage } from "../i18n-context";
import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import type { EpisodeResponse, SegmentResponse, EpisodeVocabulary } from "../contracts/podcast";
import { getEpisodeById, getSegmentById, getVocabulary } from "../api/podcast";
import { formatTime } from "../utils/formatTime";
import parsePodcastLink from "../utils/urlParser";
import VocabularySummary from "./VocabularySummary";
import InteractiveTranscript from "./transcript/InteractiveTranscript";
import YouTubeSegmentPlayer from "./YouTubeSegmentPlayer";
import { saveLastWatched } from "../utils/lastWatched";
import { getStudySources } from "../api/study";
import type { StudySource } from "../api/study";
import { verifiedCueTime, verifiedTranscriptContext } from "../utils/contextNavigation";

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
  const { t } = useLanguage();
  const location = useLocation();
  const navigate = useNavigate();
  const id = Number(segmentId);
  const search = new URLSearchParams(location.search);
  const cardId = Number(search.get("study_card"));
  const sourceId = Number(search.get("context"));
  const contextKey = Number.isInteger(cardId) && cardId !== 0 && sourceId > 0 ? `${cardId}:${sourceId}` : null;
  const [contextResult, setContextResult] = useState<{ key: string; source: StudySource | null } | null>(null);
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
    if (!contextKey) return;
    let active = true;
    void getStudySources(cardId)
      .then((sources) => { if (active) setContextResult({ key: contextKey, source: sources.find((item) => item.id === sourceId) ?? null }); })
      .catch(() => { if (active) setContextResult({ key: contextKey, source: null }); });
    return () => { active = false; };
  }, [cardId, sourceId, contextKey]);

  const contextLoading = contextKey !== null && contextResult?.key !== contextKey;
  const source = contextResult?.key === contextKey ? contextResult.source : null;
  useEffect(() => {
    if (source?.segment_id && source.segment_id !== id && source.source_status !== "missing") {
      void navigate(`/podcasts/segments/${source.segment_id}${location.search}`, { replace: true });
    }
  }, [source, id, location.search, navigate]);
  const contextRedirecting = Boolean(source?.segment_id && source.segment_id !== id && source.source_status !== "missing");

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

  if (contextRedirecting || (loadError && contextLoading)) return <p role="status">{t("Finding the original sentence…")}</p>;
  if (loadError) return <p role="alert">{t(contextKey ? "The original segment is unavailable. Your saved sentence is preserved." : loadError)}</p>;
  if (!segment) return <>{t("Loading...")}</>;
  const transcriptContext = source && segment.transcript ? verifiedTranscriptContext(segment.transcript.text, source, segment.id) : null;
  const contextTime = transcriptContext && source ? verifiedCueTime(source, segment.start_time, segment.end_time) : null;
  return (
      <div className={isPinned ? "pb-0" : "pb-36 sm:pb-0"}>
        <p className="mt-7 text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">{t("Listening practice")}</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-stone-950 sm:text-4xl">{segment.episode_title}</h1>
        <p className="mt-3 text-base text-stone-600">{segment.episode_author}</p>
        <p className="mt-4 inline-block rounded-full bg-stone-200/70 px-3 py-1 text-sm font-medium tabular-nums text-stone-700">
          {formatTime(segment.start_time)} – {formatTime(segment.end_time)}
        </p>
        {contextKey && <div role="status" className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
          {contextLoading ? t("Finding the saved sentence…") : !source || !transcriptContext ?
            t("The original sentence is unavailable or the transcript has changed. Your saved sentence is preserved.") :
            contextTime ? t("Saved sentence found · Caption starts at {time}.", { time: formatTime(contextTime.startMs / 1000) }) :
            t("Saved sentence found. An exact caption time is not available for this transcript.")}
        </div>}
        <div className="mt-8 flex flex-col gap-6">
          <section
            className={`mx-auto w-full rounded-2xl border border-stone-200 bg-white shadow-sm ${
              isPinned
                ? "sticky top-[env(safe-area-inset-top)] z-30 p-2 shadow-lg"
                : "max-w-xl p-4 sm:p-6"
            }`}
            style={isPinned ? { width: `min(${PINNED_VIDEO_SIZES[pinnedSize].width}, ${PINNED_VIDEO_SIZES[pinnedSize].percent}, calc(115.55dvh - 6.22rem))` } : undefined}
          >
            {contextLoading ? <p role="status">{t("Finding the original sentence…")}</p> : <SegmentPlayer segment={segment} isPinned={isPinned} pinnedSize={pinnedSize} onChangePinnedSize={setPinnedSize} onTogglePin={() => setIsPinned((pinned) => !pinned)} contextTime={contextTime} />}
          </section>
          {vocabularyError ? <p role="alert" className="text-sm text-red-700">{t("Could not load the vocabulary estimate.")}</p> : vocabulary ? <VocabularySummary comparison={vocabulary.segments[String(segment.id)]} baselineAt={vocabulary.baseline_at} addedAt={vocabulary.added_at} /> : <p className="text-sm text-stone-500">{t("Calculating vocabulary estimate…")}</p>}
          <InteractiveTranscript onRatingSaved={refreshVocabulary} key={`${segment.id}-${segment.episode_language}`} text={segment.transcript?.text ?? ""} language={segment.episode_language} segmentId={segment.id} context={transcriptContext} />
        </div>
      </div>
    );
}

function SegmentPlayer({ segment, isPinned, pinnedSize, onChangePinnedSize, onTogglePin, contextTime }: { segment: SegmentResponse; isPinned: boolean; pinnedSize: number; onChangePinnedSize: (size: number) => void; onTogglePin: () => void; contextTime: { startMs: number; endMs: number | null } | null }) {
  const { t } = useLanguage();
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

  if (error) return <><h2 className="text-lg font-semibold tracking-tight">{t("Player")}</h2><p role="alert" className="mt-3 text-sm text-red-700">{t("Could not load the episode player.")}</p></>;
  if (!episode) return <><h2 className="text-lg font-semibold tracking-tight">{t("Player")}</h2><p className="mt-3 text-sm text-stone-500">{t("Loading player...")}</p></>;

  const link = parsePodcastLink(episode.audio_location);
  if (link?.provider !== "youtube") {
    return <><h2 className="text-lg font-semibold tracking-tight">{t("Player")}</h2><p className="mt-3 text-sm text-stone-500">{t("Playback is currently available for YouTube episodes only.")}</p></>;
  }

  const clippedEnd = contextTime?.endMs != null && Number.isFinite(episode.duration)
    ? Math.min(contextTime.endMs, episode.duration * 1000) : null;
  const playableContext = contextTime && Number.isFinite(episode.duration) && contextTime.startMs < episode.duration * 1000 ? {
    startMs: contextTime.startMs,
    endMs: clippedEnd !== null && clippedEnd > contextTime.startMs ? clippedEnd : null,
  } : null;

  return (
    <>
      {isPinned ? (
        <div className="flex items-center justify-end gap-1">
          <button type="button" aria-label={t("Make video smaller")} disabled={pinnedSize === 0} onClick={() => onChangePinnedSize(pinnedSize - 1)} className="h-9 min-w-9 rounded-lg text-lg font-semibold text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-40">−</button>
          <button type="button" aria-label={t("Make video larger")} disabled={pinnedSize === PINNED_VIDEO_SIZES.length - 1} onClick={() => onChangePinnedSize(pinnedSize + 1)} className="h-9 min-w-9 rounded-lg text-lg font-semibold text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-40">+</button>
          <button type="button" onClick={onTogglePin} className="rounded-lg px-3 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">{t("Unpin video")}</button>
        </div>
      ) : (
        <div className="flex min-w-0 items-center justify-between gap-3">
          <h2 className="text-lg font-semibold tracking-tight">{t("Player")}</h2>
          <button type="button" onClick={onTogglePin} className="shrink-0 rounded-lg border border-stone-300 px-3 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">{t("Pin to top")}</button>
        </div>
      )}
      <YouTubeSegmentPlayer
        videoId={link.id}
        startTime={segment.start_time}
        endTime={segment.end_time}
        title={t("{title} segment", { title: segment.episode_title })}
        isPinned={isPinned}
        onPlaybackStart={handlePlaybackStart}
        contextTime={playableContext}
      />
    </>
  );
}
