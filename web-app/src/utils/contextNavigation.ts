import type { StudySource } from "../api/study";

export type TranscriptContext = {
  sentenceStart: number;
  sentenceEnd: number;
  targetStart: number;
  targetEnd: number;
};

/** Never guess by substring: verify the saved sentence and exact target span. */
export function verifiedTranscriptContext(text: string, source: StudySource, segmentId: number): TranscriptContext | null {
  if (source.source_status !== "available" || source.segment_id !== segmentId) return null;
  const { transcript_start: start, transcript_end: end, target_start: targetStart, target_end: targetEnd } = source;
  if (start === null || end === null || targetStart === null || targetEnd === null ||
      ![start, end, targetStart, targetEnd].every(Number.isInteger)) return null;
  const chars = Array.from(text);
  const sentence = Array.from(source.sentence);
  if (start < 0 || end > chars.length || start >= end || targetStart < 0 || targetStart >= targetEnd || targetEnd > sentence.length) return null;
  if (chars.slice(start, end).join("") !== source.sentence || sentence.slice(targetStart, targetEnd).join("") !== source.target_text) return null;
  return { sentenceStart: start, sentenceEnd: end, targetStart: start + targetStart, targetEnd: start + targetEnd };
}

export function verifiedCueTime(source: StudySource, segmentStart: number, segmentEnd: number): { startMs: number; endMs: number | null } | null {
  if (source.source_status !== "available" || source.timing !== "cue" || source.start_ms === null ||
      !Number.isFinite(source.start_ms) || source.start_ms < segmentStart * 1000 || source.start_ms >= segmentEnd * 1000) return null;
  const end = source.end_ms;
  // Caption cues may legitimately extend past the chunk in which they start.
  // The player caps the end against the episode duration before playback.
  return { startMs: source.start_ms, endMs: end !== null && Number.isFinite(end) && end > source.start_ms ? end : null };
}
