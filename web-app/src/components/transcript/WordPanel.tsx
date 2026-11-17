import { useLayoutEffect, useRef, useState } from "react";
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
};

export default function WordPanel({ word, language = "ja", anchor, onClose, onChange, saving }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0, ready: false });

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
  const surfaceGrammarIds = ["negative", "negative_desire", "desire", "plural", "way_of", "easy_to", "hard_to"];
  const surfaceGrammar = (word.grammar ?? []).filter((item) => surfaceGrammarIds.includes(item.id));
  const otherGrammar = (word.grammar ?? []).filter((item) => !surfaceGrammarIds.includes(item.id));
  return (
    <div ref={panelRef} className="panel" role="region" aria-label="Word details"
      style={{ top: position.top, left: position.left, visibility: position.ready ? "visible" : "hidden" }}>
      <header className="panel-header">
        <div className="panel-word"><h2 className="panel-reading" lang={language}>{language === "ja" ? word.text : word.lookup_form}{language === "ja" ? ` / ${reading || word.text}` : ""}</h2></div>
        {word.word_id !== null && <div className="panel-score" aria-live="polite">{score === -1 ? "Won’t learn" : rated ? `${score} / 5` : "Unrated"}</div>}
        <button type="button" onClick={onClose} aria-label="Close word details">×</button>
      </header>
      <section className="panel-translations" aria-label="Definitions">
        {surfaceGrammar.map((item) => <p key={`${item.id}-${item.start_idx}`}><strong>Form:</strong> {item.meaning}</p>)}
        {word.senses?.length ? language === "ja" ? <>
          {!!surfaceGrammar.length && <p>Dictionary form: <span lang="ja">{word.lookup_form}</span></p>}
          <p className="panel-primary-definition">{word.senses[0].glosses.join("; ")}</p>
          {word.senses.length > 1 && <details className="panel-other-meanings" key={`${word.start_idx}-${word.end_idx}-${word.word_id}`}>
            <summary>Other meanings</summary>
            <ol className="panel-definition-list">{word.senses.slice(1).map((sense, index) => (
              <li className="panel-definition" key={index}><span className="panel-definition-number" aria-hidden="true">{index + 2}.</span><p>{sense.glosses.join("; ")}</p></li>
            ))}</ol>
          </details>}
        </> : <ol className="panel-definition-list">{word.senses.slice(0, 3).map((sense, index) => (
          <li className="panel-definition" key={index}><span className="panel-definition-number" aria-hidden="true">{index + 1}.</span><p>{sense.glosses.join("; ")}</p></li>
        ))}</ol> : !word.grammar?.length ? <p className="panel-empty">No definitions available.</p> : null}
        {!!otherGrammar.length && <div aria-label="Grammar"><strong>Grammar</strong><ul>{otherGrammar.map((item) => <li key={`${item.id}-${item.start_idx}`}><span lang="ja">{item.text}</span> — {item.meaning}</li>)}</ul></div>}
      </section>
      {word.word_id !== null && <footer className="panel-familiarity"><fieldset disabled={saving}><RatingScale value={score} onChange={onChange} /></fieldset></footer>}
    </div>
  );
}
