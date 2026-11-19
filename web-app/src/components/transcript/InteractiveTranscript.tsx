import { useLanguage } from "../../i18n-context";
import { useEffect, useRef, useState } from "react";
import {
  fetchJapaneseTokenGroups,
  updateWordFamiliarity,
} from "../../api/japanese";
import type { TokenGroup } from "../../contracts/japanese";
import "./InteractiveTranscript.css";
import WordPanel from "./WordPanel";
import { addStudyCard, getStudyCards } from "../../api/study";
import type { StudyCard } from "../../api/study";
import { sentenceAt, sentenceOffsets } from "../../utils/studySentence";
import type { TranscriptContext } from "../../utils/contextNavigation";

export default function InteractiveTranscript({ text, language, segmentId, onRatingSaved, context }: { text: string; language: "ja" | "en"; segmentId: number; onRatingSaved?: () => void; context?: TranscriptContext | null }) {
  const { t } = useLanguage();
  const [tokens, setTokens] = useState<TokenGroup[] | null>(null);
  const [selection, setSelection] = useState<{
    index: number;
    anchor: HTMLElement;
    source: "list" | "transcript";
  } | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [studySaving, setStudySaving] = useState(false);
  const [studyError, setStudyError] = useState("");
  const [studyCards, setStudyCards] = useState<StudyCard[]>([]);
  const [attempt, setAttempt] = useState(0);
  const [page, setPage] = useState(0);
  const [guideEnabled, setGuideEnabled] = useState(true);
  const [guideTop, setGuideTop] = useState<number | null>(null);
  const transcriptRef = useRef<HTMLParagraphElement>(null);
  const contextTargetStart = context?.targetStart;

  useEffect(() => {
    if (contextTargetStart === undefined) return;
    transcriptRef.current?.querySelector<HTMLElement>("[data-context-target]")?.scrollIntoView?.({ block: "center", behavior: "smooth" });
  }, [contextTargetStart, text, tokens]);

  useEffect(() => {
    let active = true;
    void getStudyCards({ segmentId, language }).then((cards) => { if (active) setStudyCards(cards); }).catch(() => {
      // Adding remains available; the server also handles duplicate requests.
    });
    return () => { active = false; };
  }, [language, segmentId]);

  function moveGuide(clientY: number) {
    const paragraph = transcriptRef.current;
    if (!guideEnabled || !paragraph) return;
    const lineHeight = parseFloat(getComputedStyle(paragraph).lineHeight);
    const bounds = paragraph.getBoundingClientRect();
    if (!Number.isFinite(lineHeight) || lineHeight <= 0) return;
    const line = Math.max(0, Math.floor((clientY - bounds.top) / lineHeight));
    setGuideTop(line * lineHeight);
  }

  useEffect(() => {
    const clearGuide = () => setGuideTop(null);
    window.addEventListener("resize", clearGuide);
    return () => window.removeEventListener("resize", clearGuide);
  }, []);

  useEffect(() => {
    let active = true;
    setTokens(null);
    setSelection(null);
    setError("");
    setPage(0);
    setGuideTop(null);
    if (!text) return;
    fetchJapaneseTokenGroups(text, language)
      .then((groups) => {
        if (active) setTokens(groups);
      })
      .catch(() => {
        if (active) setError("Could not load word details. Please try again.");
      });
    return () => {
      active = false;
    };
  }, [text, attempt, language]);

  async function changeScore(wordId: number, score: number) {
    if (saving || !tokens) return;
    const previousScore =
      tokens.find((token) => token.word_id === wordId)?.familiarity_score ??
      null;
    setSaving(true);
    setError("");
    setTokens(
      (current) =>
        current?.map((token) =>
          token.word_id === wordId
            ? { ...token, familiarity_score: score }
            : token,
        ) ?? null,
    );
    // A word selected from the list may move off the current page immediately.
    if (selection?.source === "list") setSelection(null);
    try {
      const result = await updateWordFamiliarity(wordId, score, language);
      onRatingSaved?.();
      setTokens(
        (current) =>
          current?.map((token) =>
            token.word_id === result.word_id
              ? { ...token, familiarity_score: result.new_score }
              : token,
          ) ?? null,
      );
    } catch {
      setTokens(
        (current) =>
          current?.map((token) =>
            token.word_id === wordId
              ? { ...token, familiarity_score: previousScore }
              : token,
          ) ?? null,
      );
      setError(
        "Could not save the familiarity score. The previous score was restored.",
      );
    } finally {
      setSaving(false);
    }
  }

  const selected = selection === null ? null : tokens?.[selection.index];
  async function addSelectedSentence(sentence: string) {
    if (!selected || selected.word_id === null || studySaving) return;
    const offsets = sentenceOffsets(text, sentence, selected.start_idx, selected.end_idx);
    if (!offsets) {
      setStudyError("Choose text from this transcript that contains the selected word.");
      return;
    }
    setStudySaving(true);
    setStudyError("");
    const wordId = selected.word_id;
    const reading = selected.tokens.map((token) => token.katakana_reading).join("").normalize("NFKC")
      .replace(/[\u30A1-\u30F6]/g, (char) => String.fromCharCode(char.charCodeAt(0) - 0x60));
    try {
      const card = await addStudyCard({ word_id: wordId, segment_id: segmentId,
        dictionary_form: selected.lookup_form,
        sentence_start: offsets.start, sentence_end: offsets.end,
        target_start: selected.start_idx, target_end: selected.end_idx, reading,
        sentence: sentence.trim(), target_text: Array.from(text).slice(selected.start_idx, selected.end_idx).join("") });
      setStudyCards((cards) => [...cards.filter((item) => item.id !== card.id), card]);
      if (selected.familiarity_score === -1) {
        setTokens((current) => current?.map((token) => token.word_id === wordId ? { ...token, familiarity_score: 0 } : token) ?? null);
        if (selection?.source === "list") setSelection((current) => current?.source === "list" && current.index === selection.index ? null : current);
        onRatingSaved?.();
      }
    } catch {
      setStudyError("Could not add this sentence. Please try again.");
    } finally {
      setStudySaving(false);
    }
  }
  // Backend offsets use Unicode code points, unlike JavaScript string indices.
  const characters = Array.from(text);
  const highlighted = (part: string, offset: number): React.ReactNode => {
    if (!context || !part) return part;
    const chars = Array.from(part);
    const contextKey = `${context.sentenceStart}-${context.sentenceEnd}-${context.targetStart}-${context.targetEnd}`;
    const boundaries = [0, chars.length, context.sentenceStart - offset, context.sentenceEnd - offset,
      context.targetStart - offset, context.targetEnd - offset]
      .filter((value) => value >= 0 && value <= chars.length)
      .sort((a, b) => a - b);
    return [...new Set(boundaries)].slice(0, -1).map((start, index, unique) => {
      const end = unique[index + 1] ?? chars.length;
      const value = chars.slice(start, end).join("");
      const absolute = offset + start;
      if (absolute >= context.targetStart && absolute < context.targetEnd) {
        return <mark data-context-target key={`${contextKey}-${start}`} className="transcript-context-target">{value}</mark>;
      }
      if (absolute >= context.sentenceStart && absolute < context.sentenceEnd) {
        return <span data-context-sentence key={`${contextKey}-${start}`} className="transcript-context-sentence">{value}</span>;
      }
      return value;
    });
  };
  let position = 0;
  const content: React.ReactNode[] = [];
  tokens?.forEach((token, index) => {
    const start = Math.max(position, token.start_idx);
    const end = Math.min(characters.length, token.end_idx);
    if (start >= end) return;
    const before = characters.slice(position, start).join("");
    const word = characters.slice(start, end).join("");
    position = end;
    const score = token.familiarity_score;
    const className =
      score !== null && score >= -1 && score <= 5
        ? ` transcript-word-${score}`
        : "";
    content.push(
      highlighted(before, start - Array.from(before).length),
      token.display ? (
        <button
          key={`${token.start_idx}-${index}`}
          type="button"
          className={`transcript-word${className}`}
          aria-pressed={selection?.index === index}
          onClick={(event) => {
            setStudyError("");
            setSelection({
              index,
              anchor: event.currentTarget,
              source: "transcript",
            });
          }}
        >
          {highlighted(word, start)}
        </button>
      ) : (
        highlighted(word, start)
      ),
    );
  });

  const pages = [
    { score: 0, label: t("Unrated") },
    { score: 1, label: "1" },
    { score: 2, label: "2" },
    { score: 3, label: "3" },
    { score: -1, label: t("Won’t learn") },
  ];
  const currentPage = pages[page];
  const seenIds = new Set<number>();
  const pageWords =
    tokens?.flatMap((token, index) => {
      if (
        !token.display ||
        token.word_id === null ||
        token.familiarity_score !== currentPage.score ||
        seenIds.has(token.word_id)
      )
        return [];
      seenIds.add(token.word_id);
      return [{ token, index }];
    }) ?? [];
  return (
    <>
      <section
        className="rounded-2xl border border-stone-200 bg-white px-6 py-7 shadow-sm sm:px-10 sm:py-9"
        aria-label={t("Words in this segment")}
      >
        <div className="mx-auto max-w-3xl">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-stone-950">
                {t("Level:")} {currentPage.label}
              </h2>
              <p className="mt-1 text-sm text-stone-500" aria-live="polite">
                {t("Words from this segment")}
              </p>
            </div>
            <div className="flex gap-2" aria-label={t("Vocabulary pages")}>
              <button
                type="button"
                aria-label={t("Previous vocabulary page")}
                disabled={page === 0}
                onClick={() => {
                  setPage(page - 1);
                  setSelection(null);
                }}
                className="rounded-lg border border-stone-300 px-3 py-1.5 text-stone-700 hover:bg-stone-100 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                ←
              </button>
              <button
                type="button"
                aria-label={t("Next vocabulary page")}
                disabled={page === pages.length - 1}
                onClick={() => {
                  setPage(page + 1);
                  setSelection(null);
                }}
                className="rounded-lg border border-stone-300 px-3 py-1.5 text-stone-700 hover:bg-stone-100 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                →
              </button>
            </div>
          </div>
          {!text ? (
            <p className="mt-5 text-sm text-stone-500">
              {t("No transcript available for this segment.")}
            </p>
          ) : !tokens ? (
            <p className="mt-5 text-sm text-stone-500">
              {error ? t("Words could not be loaded.") : t("Loading words…")}
            </p>
          ) : pageWords.length === 0 ? (
            <p className="mt-5 text-sm text-stone-500">{t("No words on this page.")}</p>
          ) : (
            <div
              lang={language}
              className="mt-5 flex flex-wrap gap-2 text-base leading-normal tracking-wide sm:text-lg"
            >
              {pageWords.map(({ token, index }) => (
                <button
                  type="button"
                  key={token.word_id}
                  className={`transcript-word transcript-word-${currentPage.score}`}
                  aria-pressed={
                    selection?.source === "list" && selection.index === index
                  }
                  onClick={(event) => {
                    setStudyError("");
                    setSelection({
                      index,
                      anchor: event.currentTarget,
                      source: "list",
                    });
                  }}
                >
                  {token.text}
                </button>
              ))}
            </div>
          )}
        </div>
      </section>
      <section className="min-h-64 rounded-2xl border border-stone-200 bg-white px-6 py-7 shadow-sm sm:px-10 sm:py-9">
        <div className="mx-auto max-w-3xl">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-semibold tracking-tight text-stone-950">{t("Transcript")}</h2>
            {text && (
              <button
                type="button"
                aria-pressed={guideEnabled}
                onClick={() => {
                  setGuideEnabled((enabled) => !enabled);
                  setGuideTop(null);
                }}
                className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stone-600"
              >
                {t("Reading guide:")} {guideEnabled ? t("On") : t("Off")}
              </button>
            )}
          </div>
          {text && <p className="mt-1 text-sm text-stone-500">{t("Select a highlighted word to see its meaning.")}{guideEnabled && t(" Move over or tap a line to follow along.")}</p>}
          {text ? (
            <div className="mt-6">
              <p
                ref={transcriptRef}
                lang={language}
                className="transcript-text whitespace-pre-wrap break-words text-left text-base leading-[2] tracking-wide text-stone-800 sm:text-lg"
                onPointerMove={(event) => moveGuide(event.clientY)}
                onPointerDown={(event) => moveGuide(event.clientY)}
                onFocusCapture={(event) => {
                  const bounds = event.target.getBoundingClientRect();
                  moveGuide(bounds.top + bounds.height / 2);
                }}
              >
                {guideEnabled && guideTop !== null && (
                  <span aria-hidden="true" className="transcript-guide" style={{ top: guideTop }} />
                )}
                {tokens ? (
                  <>
                    {content}
                    {highlighted(characters.slice(position).join(""), position)}
                  </>
                ) : (
                  highlighted(text, 0)
                )}
              </p>
            </div>
          ) : (
            <p className="mt-5 text-sm text-stone-500">
              {t("No transcript available for this segment.")}
            </p>
          )}
          {text && !tokens && !error && (
            <p className="mt-3 text-sm text-stone-500" role="status">
              {t("Loading word details…")}
            </p>
          )}
          {error && (
            <p className="mt-3 text-sm text-red-700" role="alert">
              {t(error)}{" "}
              {!tokens && (
                <button
                  type="button"
                  className="underline"
                  onClick={() => {
                    setError("");
                    setAttempt((value) => value + 1);
                  }}
                >
                  {t("Retry")}
                </button>
              )}
            </p>
          )}
        </div>
      </section>
      {selected && selection && (
        <WordPanel
          key={`${selection.index}-${selection.source}`}
          word={selected}
          language={language}
          anchor={selection.anchor}
          saving={saving || studySaving}
          sentence={sentenceAt(text, selected.start_idx, selected.end_idx, language)}
          sentenceNeedsReview={!/[。！？!?.]/u.test(sentenceAt(text, selected.start_idx, selected.end_idx, language))}
          studySaving={studySaving || saving}
          studyError={t(studyError)}
          isStudied={(sentence) => {
            const offsets = sentenceOffsets(text, sentence, selected.start_idx, selected.end_idx);
            return !!offsets && studyCards.some((card) => card.word_id === selected.word_id && card.sentence_start === offsets.start && card.sentence_end === offsets.end && card.sentence === sentence.trim());
          }}
          onAddToStudy={selection.source === "transcript" && selected.word_id !== null ? (sentence) => void addSelectedSentence(sentence) : undefined}
          onClose={() => { setSelection(null); setStudyError(""); }}
          onChange={(score) => {
            if (selected.word_id !== null)
              void changeScore(selected.word_id, score);
          }}
        />
      )}
    </>
  );
}
