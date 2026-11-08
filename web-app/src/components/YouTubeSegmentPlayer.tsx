import { useEffect, useRef, useState } from "react";

type Player = {
  cueVideoById: (options: { videoId: string; startSeconds: number; endSeconds: number }) => void;
  destroy: () => void;
  getCurrentTime: () => number;
  getPlayerState: () => number;
  pauseVideo: () => void;
  seekTo: (seconds: number, allowSeekAhead: boolean) => void;
};

type YouTubeApi = {
  Player: new (element: HTMLElement, options: {
    videoId: string;
    playerVars: { origin: string; playsinline: number };
    events: {
      onReady: (event: { target: Player }) => void;
      onStateChange: (event: { data: number; target: Player }) => void;
      onError: () => void;
    };
  }) => Player;
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

export default function YouTubeSegmentPlayer({ videoId, startTime, endTime, title }: {
  videoId: string;
  startTime: number;
  endTime: number;
  title: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const lifecycle = new AbortController();
    let player: Player | undefined;
    let timer: number | undefined;
    let lastCorrection = 0;
    const container = containerRef.current;
    if (!container) return;

    const cueSegment = (target: Player) => {
      target.cueVideoById({ videoId, startSeconds: startTime, endSeconds: endTime });
    };

    void loadYouTubeApi().then((api) => {
      if (lifecycle.signal.aborted) return;
      const mount = document.createElement("div");
      container.appendChild(mount);
      player = new api.Player(mount, {
        videoId,
        playerVars: { origin: window.location.origin, playsinline: 1 },
        events: {
          onReady: ({ target }) => {
            if (lifecycle.signal.aborted) return;
            cueSegment(target);
            timer = window.setInterval(() => {
              const state = target.getPlayerState();
              if (state !== 1 && state !== 2) return;
              const time = target.getCurrentTime();
              const now = Date.now();
              if (!Number.isFinite(time)) return;
              if (time >= endTime) {
                lastCorrection = now;
                target.pauseVideo();
                cueSegment(target);
              } else if (time < startTime - 2 && now - lastCorrection >= 1500) {
                // YouTube can seek to a keyframe about two seconds early.
                lastCorrection = now;
                target.seekTo(startTime, true);
              }
            }, 200);
          },
          onStateChange: ({ data, target }) => {
            if (!lifecycle.signal.aborted && data === 0) cueSegment(target);
          },
          onError: () => {
            if (!lifecycle.signal.aborted) setError("This YouTube video cannot be played here.");
          },
        },
      });
    }).catch(() => {
      if (!lifecycle.signal.aborted) setError("Could not load the YouTube player. Please try again later.");
    });

    return () => {
      lifecycle.abort();
      if (timer !== undefined) window.clearInterval(timer);
      player?.destroy();
      container.replaceChildren();
    };
  }, [videoId, startTime, endTime]);

  return (
    <>
      <div
        ref={containerRef}
        className="mt-4 aspect-video w-full min-h-[200px] min-w-[200px] [&_iframe]:h-full [&_iframe]:w-full"
        aria-label={title}
      />
      {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    </>
  );
}
