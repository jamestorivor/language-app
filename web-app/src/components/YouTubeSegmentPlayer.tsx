import { useEffect, useRef, useState } from "react";
import { formatTime } from "../utils/formatTime";

const SKIP_SECONDS = 10;

type Player = {
  cueVideoById: (options: {
    videoId: string;
    startSeconds: number;
    endSeconds: number;
  }) => void;
  destroy: () => void;
  getCurrentTime: () => number;
  getPlayerState: () => number;
  pauseVideo: () => void;
  playVideo: () => void;
  seekTo: (seconds: number, allowSeekAhead: boolean) => void;
};

type YouTubeApi = {
  Player: new (
    element: HTMLElement,
    options: {
      videoId: string;
      playerVars: { origin: string; playsinline: number };
      events: {
        onReady: (event: { target: Player }) => void;
        onStateChange: (event: { data: number; target: Player }) => void;
        onError: () => void;
      };
    },
  ) => Player;
};

declare global {
  interface Window {
    YT?: YouTubeApi;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let apiPromise: Promise<YouTubeApi> | undefined;

function loadYouTubeApi(): Promise<YouTubeApi> {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (apiPromise) return apiPromise;

  apiPromise = new Promise<YouTubeApi>((resolve, reject) => {
    const previousReady = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      previousReady?.();
      if (window.YT?.Player) resolve(window.YT);
      else reject(new Error("YouTube player is unavailable."));
    };
    const script = document.createElement("script");
    script.src = "https://www.youtube.com/iframe_api";
    script.onerror = () => {
      script.remove();
      reject(new Error("Could not load the YouTube player."));
    };
    document.head.appendChild(script);
  }).catch((error: unknown) => {
    apiPromise = undefined;
    throw error;
  });
  return apiPromise;
}

export default function YouTubeSegmentPlayer({
  videoId,
  startTime,
  endTime,
  title,
  isPinned,
  onPlaybackStart,
}: {
  videoId: string;
  startTime: number;
  endTime: number;
  title: string;
  isPinned: boolean;
  onPlaybackStart: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<Player | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(startTime);

  useEffect(() => {
    const lifecycle = new AbortController();
    let player: Player | undefined;
    let timer: number | undefined;
    let lastCorrection = 0;
    const container = containerRef.current;
    if (!container) return;

    const cueSegment = (target: Player) => {
      target.cueVideoById({
        videoId,
        startSeconds: startTime,
        endSeconds: endTime,
      });
    };

    void loadYouTubeApi()
      .then((api) => {
        if (lifecycle.signal.aborted) return;
        const mount = document.createElement("div");
        container.appendChild(mount);
        player = new api.Player(mount, {
          videoId,
          playerVars: { origin: window.location.origin, playsinline: 1 },
          events: {
            onReady: ({ target }) => {
              if (lifecycle.signal.aborted) return;
              playerRef.current = target;
              cueSegment(target);
              setReady(true);
              timer = window.setInterval(() => {
                const state = target.getPlayerState();
                if (state !== 1 && state !== 2) return;
                const time = target.getCurrentTime();
                const now = Date.now();
                if (!Number.isFinite(time)) return;
                setCurrentTime(Math.min(endTime, Math.max(startTime, time)));
                if (time >= endTime) {
                  lastCorrection = now;
                  target.pauseVideo();
                  cueSegment(target);
                  setCurrentTime(startTime);
                } else if (
                  time < startTime - 2 &&
                  now - lastCorrection >= 1500
                ) {
                  // YouTube can seek to a keyframe about two seconds early.
                  lastCorrection = now;
                  target.seekTo(startTime, true);
                }
              }, 200);
            },
            onStateChange: ({ data, target }) => {
              if (lifecycle.signal.aborted) return;
              setPlaying(data === 1 || data === 3);
              if (data === 1) onPlaybackStart();
              if (data === 0) {
                cueSegment(target);
                setCurrentTime(startTime);
              }
            },
            onError: () => {
              if (!lifecycle.signal.aborted) {
                setReady(false);
                setPlaying(false);
                setError("This YouTube video cannot be played here.");
              }
            },
          },
        });
      })
      .catch(() => {
        if (!lifecycle.signal.aborted)
          setError(
            "Could not load the YouTube player. Please try again later.",
          );
      });

    return () => {
      lifecycle.abort();
      if (timer !== undefined) window.clearInterval(timer);
      playerRef.current = null;
      player?.destroy();
      container.replaceChildren();
    };
  }, [videoId, startTime, endTime, onPlaybackStart]);

  const skip = (seconds: number) => {
    const player = playerRef.current;
    if (!player) return;
    const current = player.getCurrentTime();
    if (!Number.isFinite(current)) return;
    const position = Math.max(startTime, Math.min(endTime, current));
    const next = Math.max(startTime, Math.min(endTime, position + seconds));
    if (next >= endTime) {
      player.pauseVideo();
      player.cueVideoById({ videoId, startSeconds: startTime, endSeconds: endTime });
      setCurrentTime(startTime);
      return;
    }
    const wasPlaying = player.getPlayerState() === 1;
    player.seekTo(next, true);
    if (!wasPlaying) player.pauseVideo();
    setCurrentTime(next);
  };

  return (
    <>
      <div
        ref={containerRef}
        className={`${isPinned ? "mt-3" : "mt-4"} aspect-video w-full overflow-hidden rounded-lg bg-stone-950 [&_iframe]:h-full [&_iframe]:w-full`}
        aria-label={title}
      />
      {error && (
        <p role="alert" className="mt-3 text-sm text-red-700">
          {error}
        </p>
      )}
      {!isPinned && <div
        role="region"
        aria-label="Playback controls"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-stone-200 bg-white/95 px-5 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] shadow-[0_-8px_24px_rgba(28,25,23,0.08)] backdrop-blur sm:hidden"
      >
        <div className="mx-auto max-w-xl">
          <div className="flex items-center justify-between gap-4 text-xs font-medium tabular-nums text-stone-500">
            <span className="min-w-0 truncate text-stone-700">{title}</span>
            <span className="shrink-0">{formatTime(currentTime)} / {formatTime(endTime)}</span>
          </div>
          <div className="mt-3 flex items-center justify-center gap-7">
            <button type="button" disabled={!ready} onClick={() => skip(-SKIP_SECONDS)} aria-label={`Back ${SKIP_SECONDS} seconds`} className="flex h-11 min-w-11 items-center justify-center rounded-full text-sm font-bold text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-40">
              −{SKIP_SECONDS}s
            </button>
            <button type="button" disabled={!ready} onClick={() => playing ? playerRef.current?.pauseVideo() : playerRef.current?.playVideo()} aria-label={playing ? "Pause" : "Play"} className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-900 text-white hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-40">
              {playing ? (
                <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-current"><path d="M6 4h4v16H6zm8 0h4v16h-4z" /></svg>
              ) : (
                <svg aria-hidden="true" viewBox="0 0 24 24" className="ml-0.5 h-5 w-5 fill-current"><path d="M6 3.5v17L19 12z" /></svg>
              )}
            </button>
            <button type="button" disabled={!ready} onClick={() => skip(SKIP_SECONDS)} aria-label={`Forward ${SKIP_SECONDS} seconds`} className="flex h-11 min-w-11 items-center justify-center rounded-full text-sm font-bold text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-40">
              +{SKIP_SECONDS}s
            </button>
          </div>
        </div>
      </div>}
    </>
  );
}
