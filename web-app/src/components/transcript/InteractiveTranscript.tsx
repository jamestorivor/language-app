import { useEffect, useState } from "react";
import {
  fetchJapaneseTokenGroups,
  updateWordFamiliarity,
} from "../../api/japanese";
import type { TokenGroup } from "../../contracts/japanese";
import "./InteractiveTranscript.css";
import WordPanel from "./WordPanel";

export default function InteractiveTranscript({ text, language }: { text: string; language: "ja" | "en" }) {
  const [tokens, setTokens] = useState<TokenGroup[] | null>(null);
  const [selection, setSelection] = useState<{
    index: number;
    anchor: HTMLElement;
    source: "list" | "transcript";
  } | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [page, setPage] = useState(0);

  useEffect(() => {
    let active = true;
    setTokens(null);
    setSelection(null);
    setError("");
    setPage(0);
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
  // Backend offsets use Unicode code points, unlike JavaScript string indices.
  const characters = Array.from(text);
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
      score !== null && score >= 0 && score <= 5
        ? ` transcript-word-${score}`
        : "";
    content.push(
      before,
      token.display ? (
        <button
          key={`${token.start_idx}-${index}`}
          type="button"
          className={`transcript-word${className}`}
          aria-pressed={selection?.index === index}
          onClick={(event) =>
            setSelection({
              index,
              anchor: event.currentTarget,
              source: "transcript",
            })
          }
        >
          {word}
        </button>
      ) : (
        word
      ),
    );
  });

  const seenIds = new Set<number>();
  const pageWords =
    tokens?.flatMap((token, index) => {
      if (
        !token.display ||
        token.word_id === null ||
        token.familiarity_score !== page ||
        seenIds.has(token.word_id)
      )
        return [];
      seenIds.add(token.word_id);
      return [{ token, index }];
    }) ?? [];
  const pageLabels = ["Not encountered", "1", "2", "3"];

  return (
    <>
      <section
        className="rounded-2xl border border-stone-200 bg-white px-6 py-7 shadow-sm sm:px-10 sm:py-9"
        aria-label="Words in this segment"
      >
        <div className="mx-auto max-w-3xl">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-stone-950">
                Level: {pageLabels[page]}
              </h2>
              <p className="mt-1 text-sm text-stone-500" aria-live="polite">
                Words from this segment
              </p>
            </div>
            <div className="flex gap-2" aria-label="Vocabulary pages">
              <button
                type="button"
                aria-label="Previous vocabulary page"
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
                aria-label="Next vocabulary page"
                disabled={page === 3}
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
              No transcript available for this segment.
            </p>
          ) : !tokens ? (
            <p className="mt-5 text-sm text-stone-500">
              {error ? "Words could not be loaded." : "Loading words…"}
            </p>
          ) : pageWords.length === 0 ? (
            <p className="mt-5 text-sm text-stone-500">No words on this page.</p>
          ) : (
            <div
              lang={language}
              className="mt-5 flex flex-wrap gap-2 text-base leading-normal tracking-wide sm:text-lg"
            >
              {pageWords.map(({ token, index }) => (
                <button
                  type="button"
                  key={token.word_id}
                  className={`transcript-word transcript-word-${page}`}
                  aria-pressed={
                    selection?.source === "list" && selection.index === index
                  }
                  onClick={(event) =>
                    setSelection({
                      index,
                      anchor: event.currentTarget,
                      source: "list",
                    })
                  }
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
          <h2 className="text-xl font-semibold tracking-tight text-stone-950">Transcript</h2>
          {text && <p className="mt-1 text-sm text-stone-500">Select a highlighted word to see its meaning.</p>}
          {text ? (
            <div className="mt-6">
              <p
                lang={language}
                className="whitespace-pre-wrap break-words text-justify text-base leading-[2] tracking-wide text-stone-800 sm:text-lg"
              >
                {tokens ? (
                  <>
                    {content}
                    {characters.slice(position).join("")}
                  </>
                ) : (
                  text
                )}
              </p>
            </div>
          ) : (
            <p className="mt-5 text-sm text-stone-500">
              No transcript available for this segment.
            </p>
          )}
          {text && !tokens && !error && (
            <p className="mt-3 text-sm text-stone-500" role="status">
              Loading word details…
            </p>
          )}
          {error && (
            <p className="mt-3 text-sm text-red-700" role="alert">
              {error}{" "}
              {!tokens && (
                <button
                  type="button"
                  className="underline"
                  onClick={() => {
                    setError("");
                    setAttempt((value) => value + 1);
                  }}
                >
                  Retry
                </button>
              )}
            </p>
          )}
        </div>
      </section>
      {selected && selection && (
        <WordPanel
          word={selected}
          language={language}
          anchor={selection.anchor}
          saving={saving}
          onClose={() => setSelection(null)}
          onChange={(score) => {
            if (selected.word_id !== null)
              void changeScore(selected.word_id, score);
          }}
        />
      )}
    </>
  );
}
