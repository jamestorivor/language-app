import { useLanguage } from "../../i18n-context";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { TokenGroup } from "../../contracts/japanese";
import RatingScale from "./RatingScale";
import "./Panel.css";

type Props = {
  word: TokenGroup;
  language?: "ja" | "en";
  anchor: HTMLElement;
  onClose: () => void;
  onChange: (score: number) => void;
  saving: boolean;
  sentence?: string;
  studySaving?: boolean;
  studyError?: string;
  sentenceNeedsReview?: boolean;
  isStudied?: (sentence: string) => boolean;
  onAddToStudy?: (sentence: string) => void;
};

export default function WordPanel({ word, language = "ja", anchor, onClose, onChange, saving, sentence, studySaving, studyError, sentenceNeedsReview, isStudied, onAddToStudy }: Props) {
  const { t } = useLanguage();
  const panelRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0, ready: false });
  const [studySentence, setStudySentence] = useState(sentence ?? "");
  const [studyPage, setStudyPage] = useState(false);
  const sentenceRef = useRef<HTMLTextAreaElement>(null);
  const studyButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (studyPage) sentenceRef.current?.focus();
  }, [studyPage]);

  useLayoutEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    function reposition() {
      if (!panel) return;
      const rect = anchor.getBoundingClientRect();
      const panelRect = panel.getBoundingClientRect();
      const spacing = 8;
      const below = rect.bottom + spacing;
      const above = rect.top - spacing - panelRect.height;
      const top = below + panelRect.height <= window.innerHeight ? below : Math.max(spacing, above);
      const left = Math.max(spacing, Math.min(rect.left, window.innerWidth - panelRect.width - spacing));
      setPosition({ top, left, ready: true });
    }
    function onPointerDown(event: PointerEvent) {
      if (!panel?.contains(event.target as Node) && !anchor.contains(event.target as Node)) onClose();
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") { onClose(); anchor.focus(); }
    }
    reposition();
    const observer = new ResizeObserver(reposition);
    observer.observe(panel);
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [anchor, onClose]);

  const reading = word.tokens.map((token) => token.katakana_reading).join("").normalize("NFKC")
    .replace(/[\u30A1-\u30F6]/g, (char) => String.fromCharCode(char.charCodeAt(0) - 0x60));
  const score = word.familiarity_score;
  const rated = score !== null && score >= 1 && score <= 5;
  return (
    <div ref={panelRef} className="panel" role="region" aria-label={studyPage ? t("Add to Study") : t("Word details")}
      style={{ top: position.top, left: position.left, visibility: position.ready ? "visible" : "hidden" }}>
      {studyPage && onAddToStudy ? <>
        <header className="panel-study-header">
          <button type="button" className="panel-study-back" onClick={() => { setStudyPage(false); requestAnimationFrame(() => studyButtonRef.current?.focus()); }}>{t("← Back")}</button>
          <h2>{t("Add to Study")}</h2>
          <button type="button" onClick={onClose} aria-label={t("Close word details")}>×</button>
        </header>
        <section className="panel-study">
          <p className="panel-study-word" lang={language}>{word.lookup_form}{language === "ja" && reading ? ` / ${reading}` : ""}</p>
          <label htmlFor="study-sentence"><strong>{t("Sentence to study")}</strong></label>
          <p>{sentenceNeedsReview ? t("No sentence boundary was found. Trim the text to the sentence you want; keep the selected word and match the transcript.") : t("Check the sentence and edit it if needed. It must contain the selected word and match the transcript.")}</p>
          <textarea ref={sentenceRef} id="study-sentence" lang={language} value={studySentence} onChange={(event) => setStudySentence(event.target.value)} rows={3} disabled={studySaving} />
          <button type="button" disabled={studySaving || !studySentence.trim() || isStudied?.(studySentence)} onClick={() => onAddToStudy(studySentence)}>
            {studySaving ? t("Adding…") : isStudied?.(studySentence) ? t("Added to study") : t("Add to Study")}
          </button>
          {studyError && <p role="alert" className="panel-study-error">{t(studyError)}</p>}
        </section>
      </> : <>
      <header className="panel-header">
        <div className="panel-word"><h2 className="panel-reading" lang={language}>{word.lookup_form}{language === "ja" ? ` / ${reading || word.text}` : ""}</h2></div>
        <div className="panel-score" aria-live="polite">{score === -1 ? t("Won’t learn") : rated ? `${score} / 5` : t("Unrated")}</div>
        <button type="button" onClick={onClose} aria-label={t("Close word details")}>×</button>
      </header>
      <section className="panel-translations" aria-label={t("Definitions")}>
        {word.senses?.length ? <ol className="panel-definition-list">{word.senses.slice(0, 3).map((sense, index) => (
          <li className="panel-definition" key={index}><span className="panel-definition-number" aria-hidden="true">{index + 1}.</span><p>{sense.glosses.join("; ")}</p></li>
        ))}</ol> : <p className="panel-empty">{t("No definitions available.")}</p>}
      </section>
      {!!word.grammar?.length && <section className="panel-translations" aria-label={t("Grammar")}><strong>{t("Grammar")}</strong><ul>{word.grammar.map((item) => <li key={`${item.id}-${item.start_idx}`}><span lang="ja">{item.text}</span> — {item.meaning}</li>)}</ul></section>}
      {word.word_id !== null && <footer className="panel-familiarity"><fieldset disabled={saving}><RatingScale value={score} onChange={onChange} onOpenStudy={onAddToStudy ? () => setStudyPage(true) : undefined} studyButtonRef={studyButtonRef} /></fieldset></footer>}
      </>}
    </div>
  );
}
