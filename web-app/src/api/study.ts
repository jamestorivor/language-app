import { API_BASE_URL } from "./config";
import { loggedFetch } from "./client";
import type { StudyShortcuts } from "../utils/studyShortcuts";

export type StudyCard = {
  id: number;
  word_id: number;
  language?: "ja" | "en";
  sentence: string;
  sentence_translation?: string | null;
  target_text: string;
  dictionary_form?: string | null;
  reading: string;
  definitions: string[];
  segment_id: number | null;
  episode_id: number | null;
  episode_title: string | null;
  sentence_start: number;
  sentence_end: number;
  target_start?: number;
  target_end?: number;
  due_at: string;
  created_at: string;
  version: number;
  state: string;
  review_status: "normal" | "deferred" | "mastered" | "wont_learn";
  next_eligible_at: string | null;
  familiarity_level: number | null;
  level_source: "auto" | "manual" | null;
  manual_level: number | null;
  is_due: boolean;
  membership_active?: boolean;
};

export type StudySource = {
  id: number;
  card_id: number;
  word_id: number;
  episode_id: number | null;
  episode_title: string | null;
  segment_id: number | null;
  sentence: string;
  target_text: string;
  target_start: number | null;
  target_end: number | null;
  sentence_start: number | null;
  sentence_end: number | null;
  transcript_start: number | null;
  transcript_end: number | null;
  start_ms: number | null;
  end_ms: number | null;
  timing: "cue" | "unknown";
  source_status: "available" | "changed" | "missing";
  dictionary_form?: string | null;
};

export type StudyStats = {
  due_count: number;
  due_today_count: number;
  completed_count: number;
};

export type StudySettings = {
  retention_percent: number;
  maximum_interval: number;
  fuzzing: boolean;
  shortcuts: StudyShortcuts;
};

export type AddStudyCard = {
  word_id: number;
  dictionary_form?: string;
  segment_id: number;
  sentence_start: number;
  sentence_end: number;
  target_start: number;
  target_end: number;
  reading: string;
  sentence: string;
  target_text: string;
};

async function request<T>(path: string, operation: string, init?: RequestInit): Promise<T> {
  const response = await loggedFetch(operation, new URL(path, API_BASE_URL), init);
  if (!response.ok) throw new Error(`Backend response ${response.status}`);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function getStudySettings() {
  return request<StudySettings>("/api/study/settings", "study.settings.get");
}

export function saveStudySettings(settings: StudySettings) {
  return request<StudySettings>("/api/study/settings", "study.settings.save", {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settings),
  });
}

// English and Japanese card IDs come from separate tables. Negative IDs keep
// them distinct in the UI while the API continues to use positive database IDs.
function clientCard(card: StudyCard): StudyCard {
  return card.language === "en" ? { ...card, id: -card.id } : card;
}

function cardPath(id: number, suffix = "") {
  return `study/cards/${Math.abs(id)}${suffix}${id < 0 ? "?language=en" : ""}`;
}

export async function getStudyCards(options: { dueOnly?: boolean; segmentId?: number; includeRemoved?: boolean; language?: "ja" | "en" } = {}) {
  const query = new URLSearchParams();
  if (options.dueOnly) query.set("due_only", "true");
  if (options.segmentId !== undefined) query.set("segment_id", String(options.segmentId));
  if (options.includeRemoved) query.set("include_removed", "true");
  const path = (language: "ja" | "en") => {
    const params = new URLSearchParams(query);
    if (language === "en") params.set("language", language);
    return `study/cards${params.size ? `?${params}` : ""}`;
  };
  if (options.language) {
    const cards = await request<StudyCard[]>(path(options.language), "study.list");
    return cards.map(clientCard);
  }
  const [japanese, english] = await Promise.all([
    request<StudyCard[]>(path("ja"), "study.list"),
    request<StudyCard[]>(path("en"), "study.list"),
  ]);
  return [...japanese, ...english.map(clientCard)].sort((a, b) => a.due_at.localeCompare(b.due_at) || a.id - b.id);
}

export async function getStudySources(cardId: number) {
  const sources = await request<StudySource[]>(cardPath(cardId, "/sources"), "study.sources");
  return cardId < 0 ? sources.map((source) => ({ ...source, card_id: -source.card_id })) : sources;
}

export async function getStudyStats(timezone?: string, language?: "ja" | "en") {
  const query = new URLSearchParams();
  if (timezone) query.set("timezone", timezone);
  if (language) {
    if (language === "en") query.set("language", "en");
    return request<StudyStats>(`study/stats${query.size ? `?${query}` : ""}`, "study.stats");
  }
  const japanese = new URLSearchParams(query);
  query.set("language", "en");
  const [ja, en] = await Promise.all([
    request<StudyStats>(`study/stats${japanese.size ? `?${japanese}` : ""}`, "study.stats"),
    request<StudyStats>(`study/stats?${query}`, "study.stats"),
  ]);
  return { due_count: ja.due_count + en.due_count, due_today_count: ja.due_today_count + en.due_today_count, completed_count: ja.completed_count + en.completed_count };
}

export async function addStudyCard(card: AddStudyCard) {
  return clientCard(await request<StudyCard>("study/cards", "study.add", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(card),
  }));
}

export async function reviewStudyCard(id: number, rating: 1 | 2 | 3 | 4, version: number) {
  return clientCard(await request<StudyCard>(cardPath(id, "/review"), "study.review", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rating, version }),
  }));
}

export function deleteStudyCard(id: number) {
  return request<void>(cardPath(id), "study.delete", { method: "DELETE" });
}

export async function updateStudyCard(id: number, card: { version: number; reading: string; definitions: string[]; sentence: string }) {
  return clientCard(await request<StudyCard>(cardPath(id), "study.update", {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(card),
  }));
}
