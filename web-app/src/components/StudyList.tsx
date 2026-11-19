import { useLanguage } from "../i18n-context";
import { useEffect, useRef, useState } from "react";
import { updateWordFamiliarity } from "../api/japanese";
import { deleteStudyCard, getStudyCards, updateStudyCard } from "../api/study";
import type { StudyCard } from "../api/study";
import StudyContext, { HighlightedSentence } from "./StudyContext";
import { useStudyLanguage } from "../utils/studyLanguage";
import "./StudyDesign.css";

type StatusFilter = "all" | "due" | "learning" | "waiting" | "mastered" | "wont_learn" | "removed";
type FamiliarityFilter = "all" | "unrated" | "1" | "2" | "3" | "4" | "5";

function statusOf(card: StudyCard): Exclude<StatusFilter, "all"> {
  if (card.membership_active === false) return "removed";
  if (card.review_status === "mastered") return "mastered";
  if (card.review_status === "wont_learn") return "wont_learn";
  if (card.is_due) return "due";
  if (card.review_status === "deferred") return "waiting";
  return "learning";
}

const statusLabels: Record<Exclude<StatusFilter, "all">, string> = {
  due: "Due now",
  learning: "Learning",
  waiting: "Waiting for review",
  mastered: "Mastered",
  wont_learn: "Won’t learn",
  removed: "Removed from Study",
};

function formatDate(value: string | null, locale: string) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" });
}

export default function StudyList() {
  const { t, locale } = useLanguage();
  const [studyLanguage] = useStudyLanguage();
  const [cards, setCards] = useState<StudyCard[]>([]);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [familiarity, setFamiliarity] = useState<FamiliarityFilter>("all");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirmRemoval, setConfirmRemoval] = useState<number | null>(null);
  const [reactivation, setReactivation] = useState<number | null>(null);
  const [reactivationLevel, setReactivationLevel] = useState("");
  const [openContext, setOpenContext] = useState<number | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState({ reading: "", definitions: "", sentence: "" });
  const requestRef = useRef(0);

  useEffect(() => {
    const request = ++requestRef.current;
    const lifecycle = new AbortController();
    setCards([]); setLoading(true); setError(""); setNotice("");
    setOpenContext(null); setEditing(null); setConfirmRemoval(null); setReactivation(null);
    void getStudyCards({ includeRemoved: true, language: studyLanguage }).then((result) => {
      if (!lifecycle.signal.aborted && request === requestRef.current) setCards(result);
    }).catch(() => {
      if (!lifecycle.signal.aborted && request === requestRef.current) setError("Could not load your study list. Please try again.");
    }).finally(() => {
      if (!lifecycle.signal.aborted && request === requestRef.current) setLoading(false);
    });
    return () => lifecycle.abort();
  }, [studyLanguage]);

  async function refresh() {
    const request = ++requestRef.current;
    setLoading(true);
    setError("");
    try {
      const result = await getStudyCards({ includeRemoved: true, language: studyLanguage });
      if (request === requestRef.current) setCards(result);
    } catch {
      if (request === requestRef.current) setError("Could not load your study list. Please try again.");
    } finally {
      if (request === requestRef.current) setLoading(false);
    }
  }

  async function updateLevel(card: StudyCard, level: number) {
    if (busy !== null) return;
    setBusy(card.id);
    setError("");
    setNotice("");
    try {
      await updateWordFamiliarity(card.word_id, level, card.language ?? "ja");
      setReactivation(null);
      setReactivationLevel("");
      setNotice(level === 5 ? "Marked as mastered. All cards for this word are paused." : "Familiarity updated. All cards for this word use the new level.");
      await refresh();
    } catch {
      setError("Could not update familiarity. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  async function saveCard(card: StudyCard) {
    if (busy !== null || !draft.sentence.trim()) return;
    setBusy(card.id);
    setError("");
    setNotice("");
    try {
      const updated = await updateStudyCard(card.id, {
        version: card.version, reading: draft.reading,
        definitions: draft.definitions.split("\n").map((item) => item.trim()).filter(Boolean),
        sentence: draft.sentence,
      });
      setCards((current) => current.map((item) => item.id === card.id ? updated : item));
      setEditing(null);
      setNotice("Card updated.");
    } catch {
      setError("Could not save this card. It may have changed elsewhere; refresh and try again.");
    } finally {
      setBusy(null);
    }
  }

  async function remove(card: StudyCard) {
    if (busy !== null) return;
    setBusy(card.id);
    setError("");
    setNotice("");
    try {
      await deleteStudyCard(card.id);
      setConfirmRemoval(null);
      setCards((current) => current.map((item) => item.id === card.id ? { ...item, membership_active: false, is_due: false } : item));
      setNotice("Card removed from study. Its review history is saved if you add it again.");
    } catch {
      setError("Could not remove this card. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  const visible = cards.filter((card) => {
    const statusMatches = status === "all" ? card.membership_active !== false : statusOf(card) === status;
    const levelMatches = familiarity === "all" || (familiarity === "unrated"
      ? card.familiarity_level === null
      : card.familiarity_level === Number(familiarity));
    return statusMatches && levelMatches;
  });

  return <div className="study-list-shell mx-auto max-w-3xl">
    <h1 className="text-lg font-semibold text-stone-900">{t("Study List")}</h1>
    <div className="study-filters mt-6 grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-semibold text-stone-700">{t("Status")}
        <select value={status} onChange={(event) => setStatus(event.target.value as StatusFilter)} className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 font-normal focus:outline-2 focus:outline-emerald-800">
          <option value="all">{t("All active statuses")}</option><option value="due">{t("Due now")}</option><option value="learning">{t("Learning")}</option><option value="waiting">{t("Waiting for review")}</option><option value="mastered">{t("Mastered")}</option><option value="wont_learn">{t("Won’t learn")}</option><option value="removed">{t("Removed from Study")}</option>
        </select>
      </label>
      <label className="text-sm font-semibold text-stone-700">{t("Familiarity")}
        <select value={familiarity} onChange={(event) => setFamiliarity(event.target.value as FamiliarityFilter)} className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 font-normal focus:outline-2 focus:outline-emerald-800">
          <option value="all">{t("All levels")}</option><option value="unrated">{t("Unrated")}</option><option value="1">{t("Level 1")}</option><option value="2">{t("Level 2")}</option><option value="3">{t("Level 3")}</option><option value="4">{t("Level 4")}</option><option value="5">{t("Level 5")}</option>
        </select>
      </label>
    </div>
    {error && <p role="alert" className="mt-5 text-sm text-red-700">{t(error)} <button type="button" onClick={() => void refresh()} className="ml-2 rounded-lg border border-red-200 bg-white px-3 py-1 font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700">{t("Retry")}</button></p>}
    {notice && <p role="status" className="mt-5 text-sm text-emerald-800">{t(notice)}</p>}
    {loading ? <p className="mt-8 text-stone-500" role="status">{t("Loading study list…")}</p> : !cards.length ? (
      <p className="mt-8 text-stone-600">{t("Your Study List is empty. Choose a word in a transcript and select Add to Study.")}</p>
    ) : !visible.length ? (
      <p className="mt-8 text-stone-600">{t("No cards match these filters.")}</p>
    ) : <>
      <p className="mt-6 text-sm text-stone-500" aria-live="polite">{t(visible.length === 1 ? "{count} card" : "{count} cards", { count: visible.length })}</p>
      <ul className="study-entries mt-3 space-y-3">{visible.map((card) => {
        const cardStatus = statusOf(card);
        const next = formatDate(card.next_eligible_at, locale);
        const suspended = cardStatus === "mastered" || cardStatus === "wont_learn";
        const removed = cardStatus === "removed";
        return <li key={card.id} className={`study-entry study-entry-${cardStatus} rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-6`}>
          <div className="study-entry-heading flex flex-wrap items-start justify-between gap-3">
            <div><h2 lang={card.language ?? "ja"} className="text-xl font-semibold text-stone-950">{card.target_text}</h2>{card.reading && <p lang={card.language ?? "ja"} className="mt-1 text-sm text-stone-600">{card.reading}</p>}</div>
            <span className="study-status rounded-full bg-stone-100 px-3 py-1 text-xs font-semibold text-stone-700">{t(statusLabels[cardStatus])}</span>
          </div>
          <p className="study-entry-meaning mt-3 text-stone-700">{card.definitions.length ? card.definitions.join("; ") : t("No definition available.")}</p>
          {openContext !== card.id && <p lang={card.language ?? "ja"} className="study-entry-sentence mt-3 whitespace-pre-wrap text-stone-700"><HighlightedSentence text={card.sentence} target={card.target_text} start={card.target_start === undefined ? null : card.target_start - card.sentence_start} end={card.target_end === undefined ? null : card.target_end - card.sentence_start} /></p>}
          <div className="study-level-meter" aria-hidden="true">
            {[1, 2, 3, 4, 5].map((level) => <span key={level} className={card.familiarity_level !== null && level <= card.familiarity_level ? "filled" : ""} />)}
          </div>
          <p className="study-entry-progress mt-3 text-sm text-stone-500">{card.familiarity_level === null ? t("Unrated") : t("Familiarity {level} / 5", { level: card.familiarity_level })}{next && !suspended && !removed ? ` · ${t(card.is_due ? "Due since" : "Next review")}: ${next}` : ""}</p>
          <button type="button" aria-expanded={openContext === card.id} aria-label={t("View sources for {word}", { word: card.target_text })} onClick={() => setOpenContext(openContext === card.id ? null : card.id)} className="mt-4 rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">{openContext === card.id ? t("Hide sources") : t("View sources")}</button>
          {openContext === card.id && <StudyContext key={card.id} card={card} />}
          <div className="study-entry-actions mt-4 flex flex-wrap items-center gap-2 text-sm">
            <button type="button" disabled={busy !== null} aria-label={t("Edit {word}", { word: card.target_text })} onClick={() => { setEditing(card.id); setDraft({ reading: card.reading, definitions: card.definitions.join("\n"), sentence: card.sentence }); setConfirmRemoval(null); setReactivation(null); }} className="rounded-lg border border-emerald-800 bg-emerald-50 px-3 py-2 font-semibold text-emerald-900 hover:bg-emerald-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50">{t("Edit card")}</button>
            {!removed && (suspended ? <button type="button" disabled={busy !== null} onClick={() => { setReactivation(card.id); setReactivationLevel(""); setConfirmRemoval(null); }} aria-label={t("Reactivate {word}", { word: card.target_text })} className="rounded-lg border border-stone-300 bg-white px-3 py-2 font-semibold text-stone-700 hover:bg-stone-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50">{t("Reactivate")}</button> : <button type="button" disabled={busy !== null} onClick={() => void updateLevel(card, 5)} aria-label={t("Mark {word} as mastered", { word: card.target_text })} className="rounded-lg border border-stone-300 bg-white px-3 py-2 font-semibold text-stone-700 hover:bg-stone-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50">{t("Mark as mastered")}</button>)}
            {!removed && <button type="button" disabled={busy !== null} onClick={() => { setConfirmRemoval(card.id); setReactivation(null); }} aria-label={t("Remove {word} from study", { word: card.target_text })} className="rounded-lg border border-red-200 bg-white px-3 py-2 font-semibold text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700 disabled:opacity-50">{t("Remove from study")}</button>}
          </div>
          {editing === card.id && <form className="mt-4 space-y-4 rounded-xl border border-stone-200 bg-stone-50 p-4" onSubmit={(event) => { event.preventDefault(); void saveCard(card); }}>
            <h3 className="font-semibold text-stone-900">{t("Edit card")}</h3>
            <p className="text-sm text-stone-600">{t("Changes apply to this card. The original source is kept.")}</p>
            <label className="block text-sm font-semibold text-stone-700">{t("Reading")}
              <input lang={card.language ?? "ja"} value={draft.reading} maxLength={500} onChange={(event) => setDraft({ ...draft, reading: event.target.value })} className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 font-normal" />
            </label>
            <label className="block text-sm font-semibold text-stone-700">{t("Definitions")} <span className="font-normal text-stone-500">{t("(one per line)")}</span>
              <textarea value={draft.definitions} onChange={(event) => setDraft({ ...draft, definitions: event.target.value })} rows={3} className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 font-normal" />
            </label>
            <label className="block text-sm font-semibold text-stone-700">{t("Study sentence")}
              <textarea lang={card.language ?? "ja"} required maxLength={10000} value={draft.sentence} onChange={(event) => setDraft({ ...draft, sentence: event.target.value })} rows={3} className="mt-1 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 font-normal" />
            </label>
            <div className="flex flex-wrap gap-2">
              <button type="submit" disabled={busy !== null || !draft.sentence.trim()} className="rounded-lg bg-emerald-900 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{t("Save changes")}</button>
              <button type="button" disabled={busy !== null} onClick={() => setEditing(null)} className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-100 disabled:opacity-50">{t("Cancel editing")}</button>
            </div>
          </form>}
          {!removed && <p className="mt-2 text-xs text-stone-500">{t("Familiarity applies to all cards for this word. Removing a card affects only this sentence.")}</p>}
          {reactivation === card.id && <div className="mt-4 rounded-xl bg-stone-50 p-4">
            <p className="text-sm text-stone-600">{t("Choose a familiarity level to reactivate all cards for this word. Their review histories are kept.")}</p>
            <div className="mt-3 flex flex-wrap items-end gap-3">
              <label className="text-sm font-semibold text-stone-700">{t("New familiarity level")}
                <select value={reactivationLevel} onChange={(event) => setReactivationLevel(event.target.value)} className="mt-1 block rounded-lg border border-stone-300 bg-white px-3 py-2 font-normal">
                  <option value="">{t("Choose a level")}</option><option value="1">{t("1 — Unknown")}</option><option value="2">{t("2 — Learning")}</option><option value="3">{t("3 — Familiar")}</option><option value="4">{t("4 — Very familiar")}</option>
                </select>
              </label>
              <button type="button" disabled={!reactivationLevel || busy !== null} onClick={() => void updateLevel(card, Number(reactivationLevel))} className="rounded-lg bg-emerald-900 px-4 py-2 font-semibold text-white disabled:opacity-50">{t("Confirm reactivation")}</button>
              <button type="button" disabled={busy !== null} onClick={() => setReactivation(null)} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-stone-700 hover:bg-stone-100">{t("Cancel")}</button>
            </div>
          </div>}
          {confirmRemoval === card.id && <div className="mt-4 rounded-xl bg-stone-50 p-4 text-sm">
            <p>{t("Remove this card from study? Its history will be kept.")}</p>
            <div className="mt-3 flex gap-4"><button type="button" disabled={busy !== null} onClick={() => void remove(card)} className="rounded-lg bg-red-700 px-3 py-2 font-semibold text-white hover:bg-red-800 disabled:opacity-50">{t("Confirm removal")}</button><button type="button" disabled={busy !== null} onClick={() => setConfirmRemoval(null)} className="rounded-lg border border-stone-300 bg-white px-3 py-2 font-semibold text-stone-700 hover:bg-stone-100">{t("Cancel")}</button></div>
          </div>}
        </li>;
      })}</ul>
    </>}
  </div>;
}
