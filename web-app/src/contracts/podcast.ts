import type { PodcastLink } from "../utils/urlParser";
import type { TranscriptFileFormat } from "../utils/transcriptFile";

export type PodcastLanguage = "ja" | "en";

// Matches the podcast API schemas in backend/app/schemas.py.
export type CreateEpisodeRequest = {
  audio_location: string;
  title: string;
  author: string;
  chunk_interval: number;
  podcast_details: PodcastLink;
  language: PodcastLanguage;
  external_transcript?: string;
  external_transcript_format?: TranscriptFileFormat;
};

export type EpisodeResponse = Omit<
  CreateEpisodeRequest,
  "chunk_interval" | "podcast_details" | "external_transcript" | "external_transcript_format"
> & {
  id: number;
  user_id: number;
  duration: number;
  added_at: string | null;
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

export type VocabularyEstimate = {
  coverage_low: number;
  coverage_high: number;
  coverage_occurrences: number;
  known_occurrences: number;
  uncertain_occurrences: number;
  uncertain_rated_unique: number;
  familiarity_low: number;
  familiarity_high: number;
  difficulty_low: number;
  difficulty_high: number;
  rated_percent: number;
  matched_occurrences: number;
  unmatched_groups: number;
  dictionary_match_percent: number;
  unrated_unique: number;
  low_rated_unique: number;
};

export type VocabularyComparison = {
  baseline: VocabularyEstimate | null;
  current: VocabularyEstimate | null;
  improved_unique: number;
  declined_unique: number;
  newly_rated_unique: number;
};

export type EpisodeVocabulary = {
  added_at: string | null;
  baseline_at: string | null;
  segments_with_text: number;
  segment_count: number;
  episode: VocabularyComparison | null;
  segments: Record<string, VocabularyComparison>;
};
