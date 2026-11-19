import { useLanguage } from "../i18n-context";
import { useCallback, useEffect, useRef, useState } from "react";
import { deleteStudyCard, getStudyCards, getStudySettings, reviewStudyCard } from "../api/study";
import type { StudyCard } from "../api/study";
import { updateWordFamiliarity } from "../api/japanese";
import StudyContext from "./StudyContext";
import { useStudyLanguage } from "../utils/studyLanguage";
import { eventShortcut, shortcutLabel } from "../utils/studyShortcuts";
import type { StudyShortcuts } from "../utils/studyShortcuts";
import "./StudyDesign.css";



function localTime(value: string | null | undefined, locale: string) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" });
}

export default function Study() {
  const { t, locale } = useLanguage();
  const [studyLanguage] = useStudyLanguage();
  const grades = [
    { rating: 1, action: "again", label: t("Again"), description: t("Forgot") },
    { rating: 2, action: "hard", label: t("Hard"), description: t("Remembered with difficulty") },
    { rating: 3, action: "good", label: t("Good"), description: t("Remembered") },
    { rating: 4, action: "easy", label: t("Easy"), description: t("Remembered easily") },
  ] as const;
  const [shortcuts, setShortcuts] = useState<StudyShortcuts | null>(null);
  const [shortcutError, setShortcutError] = useState(false);
  const [shortcutAttempt, setShortcutAttempt] = useState(0);
  const [cards, setCards] = useState<StudyCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [queueAvailable, setQueueAvailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const requestNumber = useRef(0);
  const reviewInFlight = useRef(false);

  const load = useCallback(async () => {
    const request = ++requestNumber.current;
    try {
      const due = await getStudyCards({ dueOnly: true, language: studyLanguage });
      if (request !== requestNumber.current) return;
      setCards(due);
      setQueueAvailable(true);
    } catch {
      if (request === requestNumber.current) {
        setQueueAvailable(false);
        setError("Could not load your review queue. Please refresh and try again.");
      }
    } finally {
      if (request === requestNumber.current) setLoading(false);
    }
  }, [studyLanguage]);

  useEffect(() => {
    const lifecycle = new AbortController();
    const request = ++requestNumber.current;
    void getStudyCards({ dueOnly: true, language: studyLanguage })
      .then((due) => {
        if (lifecycle.signal.aborted || request !== requestNumber.current) return;
        setCards(due);
        setQueueAvailable(true);
      })
      .catch(() => {
        if (!lifecycle.signal.aborted && request === requestNumber.current) {
          setQueueAvailable(false);
          setError("Could not load your review queue. Please refresh and try again.");
        }
      })
      .finally(() => {
        if (!lifecycle.signal.aborted && request === requestNumber.current) setLoading(false);
      });
    return () => lifecycle.abort();
  }, [studyLanguage]);

  useEffect(() => {
    let active = true;
    void getStudySettings().then((settings) => {
      if (active) setShortcuts(settings.shortcuts);
    }).catch(() => {
      if (active) { setShortcuts(null); setShortcutError(true); }
    });
    return () => { active = false; };
  }, [shortcutAttempt]);

  function reload() {
    setError("");
    setLoading(true);
    setRevealed(false);
    setConfirmRemove(false);
    void load();
  }

  const review = useCallback(async (card: StudyCard, rating: 1 | 2 | 3 | 4) => {
    if (busy || reviewInFlight.current) return;
    reviewInFlight.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await reviewStudyCard(card.id, rating, card.version);
      const next = localTime(result.next_eligible_at, locale);
      const familiarityChange = result.familiarity_level && result.familiarity_level !== card.familiarity_level
        ? t(" Familiarity is now level {level}.", { level: result.familiarity_level }) : "";
      setNotice(`${next ? t("Review saved. Next review: {date}.", { date: next }) : t("Review saved.")}${familiarityChange}`);
      setCards((current) => result.is_due
        ? current.map((item) => item.id === card.id ? result : item)
        : current.filter((item) => item.id !== card.id));
      setRevealed(false);
      setLoading(true);
      await load();
    } catch {
      // A conflict can mean another session has already changed this card.
      setError("Could not save the review. The queue has been refreshed; please try again if the card is still due.");
      setRevealed(false);
      setLoading(true);
      await load();
    } finally {
      reviewInFlight.current = false;
      setBusy(false);
    }
  }, [busy, load, locale, t]);

  async function remove(card: StudyCard) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await deleteStudyCard(card.id);
      setNotice("Card removed from Study. Its review history is saved.");
      setCards((current) => current.filter((item) => item.id !== card.id));
      setConfirmRemove(false);
      setRevealed(false);
      setLoading(true);
      await load();
    } catch {
      setError("Could not remove this card. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function master(card: StudyCard) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await updateWordFamiliarity(card.word_id, 5, card.language ?? "ja");
      setNotice("Word marked as mastered. You can reactivate it from your Study List.");
      setCards((current) => current.filter((item) => item.word_id !== card.word_id || item.language !== card.language));
      setRevealed(false);
      setConfirmRemove(false);
      setLoading(true);
      await load();
    } catch {
      setError("Could not mark this word as mastered. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const card = cards[0];
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!card || !shortcuts || loading || !queueAvailable || busy || reviewInFlight.current || confirmRemove ||
          event.defaultPrevented || event.repeat || event.isComposing || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="textbox"]')) return;
      const key = eventShortcut(event);
      // Preserve the native behavior of focused buttons and links for navigation keys.
      if (["Enter", "Space", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(key) &&
          target?.closest('button, a, summary, [role="button"], [role="link"]')) return;
      if (!revealed && key === shortcuts.show_answer) {
        event.preventDefault();
        setRevealed(true);
      } else if (revealed) {
        const ratings: [string, 1 | 2 | 3 | 4][] = [[shortcuts.again, 1], [shortcuts.hard, 2], [shortcuts.good, 3], [shortcuts.easy, 4]];
        const rating = ratings.find(([binding]) => binding === key)?.[1];
        if (rating !== undefined) {
          event.preventDefault();
          void review(card, rating);
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [card, shortcuts, loading, queueAvailable, busy, confirmRemove, revealed, review]);
  const familiarity = card?.familiarity_level;
  return (
    <div className="review-shell mx-auto max-w-3xl">
      {shortcutError && <p role="alert" className="mt-5 text-sm text-amber-800">{t("Could not load keyboard shortcuts. Review buttons still work.")} <button type="button" onClick={() => { setShortcutError(false); setShortcutAttempt((value) => value + 1); }} className="font-semibold underline">{t("Try again")}</button></p>}
      {error && <p role="alert" className="mt-5 text-sm text-red-700">{t(error)} <button type="button" disabled={busy} onClick={reload} className="font-semibold underline">{t("Refresh")}</button></p>}
      {notice && <p role="status" className="mt-5 text-sm text-emerald-800">{t(notice)}</p>}
      {loading ? <p className="mt-8 text-stone-500" role="status">{t("Loading cards…")}</p> : !queueAvailable ? null : card ? (
        <section className="review-card mt-6 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm sm:p-8" aria-label={t("Review card")}>
          <div className="review-card-meta flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-stone-500">{t(cards.length === 1 ? "{count} card due" : "{count} cards due", { count: cards.length })}</p>
            <button type="button" disabled={busy || loading} onClick={reload} className="text-xs font-semibold text-stone-500 hover:text-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50">{t("Refresh")}</button>
            <p className="rounded-full bg-stone-100 px-3 py-1 text-xs font-semibold text-stone-700" aria-label={familiarity ? t("Familiarity {level} of 5", { level: familiarity }) : t("Familiarity unrated")}>{familiarity ? t("Familiarity {level} / 5", { level: familiarity }) : t("Unrated")}</p>
          </div>
          <div className="review-prompt">
          <h2 className="mt-8 break-words text-3xl font-bold leading-relaxed text-stone-950 sm:text-4xl" lang={card.language ?? "ja"}>{card.target_text}</h2>
          {card.reading && card.reading !== card.target_text && <p className="mt-2 text-lg text-stone-500" lang={card.language ?? "ja"}>{card.reading}</p>}

          </div>

          {!revealed ? (
            <button type="button" aria-keyshortcuts={shortcuts?.show_answer} onClick={() => setRevealed(true)} disabled={busy} className="review-reveal mt-8 w-full rounded-xl bg-emerald-900 px-5 py-3 font-semibold text-white hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50 sm:w-auto">{t("Show answer")} {shortcuts && <kbd aria-hidden="true">{t(shortcutLabel(shortcuts.show_answer))}</kbd>}</button>
          ) : (
            <div className="review-answer mt-8 border-t border-stone-200 pt-6" aria-label={t("Answer")}>
              <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-stone-500">{t("Meaning")}</h3>
              <p className="mt-2 text-lg text-stone-900">{card.definitions.length ? card.definitions.join("; ") : t("No definition available.")}</p>
              <StudyContext key={card.id} card={card} compact />
              <fieldset disabled={busy} className="review-controls" aria-label={t("How well did you remember?")}>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{grades.map(({ rating, label, description, action }) => (
                  <button key={rating} type="button" aria-keyshortcuts={shortcuts?.[action]} onClick={() => void review(card, rating)} aria-label={`${label}: ${description}`} className={`review-grade review-grade-${rating} rounded-lg border px-2 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50`}><span>{description}</span>{shortcuts && <kbd aria-hidden="true">{t(shortcutLabel(shortcuts[action]))}</kbd>}</button>
                ))}</div>
              </fieldset>
            </div>
          )}

          <div className="review-secondary mt-8 flex flex-wrap items-center gap-x-5 gap-y-3 border-t border-stone-100 pt-5 text-sm">
            <button type="button" disabled={busy} onClick={() => void master(card)} className="font-semibold text-stone-700 underline hover:text-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50">{t("Mark as Mastered")}</button>
            {confirmRemove ? <span className="flex flex-wrap items-center gap-3"><span>{t("Remove this card from Study?")}</span><button type="button" disabled={busy} onClick={() => void remove(card)} className="font-semibold text-red-700 underline disabled:opacity-50">{t("Remove")}</button><button type="button" disabled={busy} onClick={() => setConfirmRemove(false)} className="underline disabled:opacity-50">{t("Cancel")}</button></span> : <button type="button" disabled={busy} onClick={() => setConfirmRemove(true)} className="text-stone-600 underline hover:text-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50">{t("Remove from Study")}</button>}
          </div>
          <p className="mt-3 text-xs text-stone-500">{t("Marking a word mastered pauses review of all its sentence cards. Your history is kept.")}</p>
        </section>
      ) : (
        <section className="mt-6 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="text-lg font-semibold text-stone-900">{t("No cards are due right now")}</h2>
          <p className="mt-2 text-sm text-stone-600">{t("Your next review will appear here when it’s ready. You can add sentences from a transcript.")}</p>
        </section>
      )}
    </div>
  );
}
