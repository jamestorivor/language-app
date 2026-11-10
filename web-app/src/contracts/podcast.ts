import type { PodcastLink } from "../utils/urlParser";

export type PodcastLanguage = "ja" | "en";

// Matches the podcast API schemas in backend/app/schemas.py.
export type CreateEpisodeRequest = {
  audio_location: string;
  title: string;
  author: string;
  chunk_interval: number;
  podcast_details: PodcastLink;
  language: PodcastLanguage;
};

export type EpisodeResponse = Omit<
  CreateEpisodeRequest,
  "chunk_interval" | "podcast_details"
> & {
  id: number;
  user_id: number;
  duration: number;
};

// Chunk times are numeric offsets; end_time must be greater than start_time.
export type CreateSegmentRequest = {
  start_time: number;
  end_time: number;
};

export type CreateTranscriptRequest = {
  text: string;
};

export type TranscriptResponse = CreateTranscriptRequest & {
  id: number;
  podcast_chunk_id: number;
};

export type SegmentResponse = CreateSegmentRequest & {
  id: number;
  user_id: number;
  podcast_id: number;
  episode_title: string;
  episode_author: string;
  episode_language: PodcastLanguage;
  transcript: TranscriptResponse | null;
};

export type ListSegmentResponse = SegmentResponse[];
