import type { EpisodeResponse } from "../contracts/podcast";

function storageKey(episode: EpisodeResponse): string {
  return `last-watched:${episode.user_id}:${episode.id}:${episode.audio_location}`;
}

export function saveLastWatched(episode: EpisodeResponse, segmentStart: number): void {
  try {
    window.localStorage.setItem(storageKey(episode), String(segmentStart));
  } catch {
    // Playback should still work if browser storage is unavailable.
  }
}

export function getLastWatched(episode: EpisodeResponse): number | null {
  try {
    const value = window.localStorage.getItem(storageKey(episode));
    if (value === null || value.trim() === "") return null;
    const segmentStart = Number(value);
    return Number.isFinite(segmentStart) && segmentStart >= 0 ? segmentStart : null;
  } catch {
    return null;
  }
}
