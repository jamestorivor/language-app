import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router";
import type { SegmentResponse } from "../contracts/podcast";
import { getSegmentById } from "../api/podcast";
import { formatTime } from "../utils/formatTime";
import InteractiveTranscript from "./transcript/InteractiveTranscript";

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

  useEffect(() => {
    async function loadSegment(segmentId: number) {
      const segment = await getSegmentById(segmentId);
      setSegment(segment);
    }
    if (!segment) {
      void loadSegment(id);
    }
  }, []);

  if (!segment) return <>Loading...</>;
  else
    return (
      <div>
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
        <div className="mt-8 grid gap-6">
          <section className="mx-auto w-full max-w-xl rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-semibold tracking-tight">Player</h2>
            <p className="mt-1 text-sm text-stone-500">
              Audio will appear here when a podcast is added.
            </p>
            <audio
              className="mx-auto mt-4 block w-full max-w-md"
              controls
              preload="none"
              aria-label="Podcast audio"
            >
              Your browser does not support audio playback.
            </audio>
          </section>
          <InteractiveTranscript key={segment.id} text={segment.transcript?.text ?? ""} />
        </div>
      </div>
    );
}
