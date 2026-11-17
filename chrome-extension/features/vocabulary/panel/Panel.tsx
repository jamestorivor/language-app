import { useEffect, useLayoutEffect, useRef, useState } from "react";
import "./Panel.css";
import getPanelPosition from "./panel-position.ts";
import RatingScale from "./RatingScale.tsx";
import type { TokenGroup } from "@/contracts/parse-japanese.ts";
import type { LocalJapStorage } from "@/contracts/jap-vocab.ts";

export interface selectionData {
  wordToken: TokenGroup;
  rect: DOMRect;
}

type PanelProps = {
  localJapDb: LocalJapStorage;
  language: "ja" | "en";
  onFamiliarityChange: (wordId: number, newScore: number) => Promise<void>;
};

function katakanaToHiragana(text: string): string {
  return text
    .normalize("NFKC")
    .replace(/[\u30A1-\u30F6]/g, (char) =>
      String.fromCharCode(char.charCodeAt(0) - 0x60),
    );
}

function panelContent(
  wordToken: TokenGroup,
  wordRect: DOMRect,
  panelData: { height: number; width: number },
  windowData: { height: number; width: number },
  panelRef: React.RefObject<HTMLDivElement | null>,
  onChange: (score: number) => void,
  language: "ja" | "en",
  saving: boolean,
  error: string,
) {
  if (!wordToken || !wordRect || !panelData || !windowData) return;
  else {
    const panelPosition: { x: number; y: number } = getPanelPosition(
      wordRect,
      windowData.height,
      windowData.width,
      panelData.height,
      panelData.width,
    );
    const reading = katakanaToHiragana(
      wordToken.tokens.map((token) => token.katakana_reading).join(""),
    );
    const senses = wordToken.senses ?? [];
    const score = wordToken.familiarity_score;
    const isRated = score != null && score >= 1 && score <= 5;
    const surfaceGrammarIds = ["negative", "negative_desire", "desire", "plural", "way_of", "easy_to", "hard_to"];
    const surfaceGrammar = (wordToken.grammar ?? []).filter((item) => surfaceGrammarIds.includes(item.id));
    const otherGrammar = (wordToken.grammar ?? []).filter((item) => !surfaceGrammarIds.includes(item.id));
    return (
      <div
        ref={panelRef}
        className="panel"
        role="region"
        aria-label="Word details"
        style={{
          top: panelPosition.y,
          left: panelPosition.x,
        }}
      >
        <header className="panel-header">
          <div className="panel-word">
            <h2 className="panel-reading" lang={language}>
              {language === "ja" ? wordToken.text : wordToken.lookup_form}{language === "ja" ? ` / ${reading || wordToken.text}` : ""}
            </h2>
          </div>
          {wordToken.word_id !== null && <div className="panel-score" aria-live="polite">
            <span
              className="panel-score-value"
              aria-label={isRated ? `Familiarity ${score} of 5` : score === -1 ? "Won’t learn" : "Unrated"}
            >
              {isRated ? (
                <>
                  {score}
                  <span className="panel-score-total"> / 5</span>
                </>
              ) : (
                score === -1 ? "Won’t learn" : "Unrated"
              )}
            </span>
          </div>}
        </header>
        <section className="panel-translations" aria-label="Definitions">
          {surfaceGrammar.map((item) => <p key={`${item.id}-${item.start_idx}`}><strong>Form:</strong> {item.meaning}</p>)}
          {senses.length > 0 && language === "ja" ? (
            <>
              {surfaceGrammar.length > 0 && <p>Dictionary form: <span lang="ja">{wordToken.lookup_form}</span></p>}
              <p className="panel-primary-definition">{senses[0]?.glosses.join("; ")}</p>
              {senses.length > 1 && (
                <details className="panel-other-meanings" key={`${wordToken.start_idx}-${wordToken.end_idx}-${wordToken.word_id}`}>
                  <summary>Other meanings</summary>
                  <ol className="panel-definition-list">
                    {senses.slice(1).map((sense, index) => (
                      <li className="panel-definition" key={index}>
                        <span className="panel-definition-number" aria-hidden="true">{index + 2}.</span>
                        <p>{sense.glosses.join("; ")}</p>
                      </li>
                    ))}
                  </ol>
                </details>
              )}
            </>
          ) : senses.length > 0 ? (
            <ol className="panel-definition-list">
              {senses.slice(0, 3).map((sense, index) => (
                <li className="panel-definition" key={index}>
                  <span className="panel-definition-number" aria-hidden="true">
                    {index + 1}.
                  </span>
                  <p>{sense.glosses.join("; ")}</p>
                </li>
              ))}
            </ol>
          ) : !wordToken.grammar?.length ? (
            <p className="panel-empty">No definitions available.</p>
          ) : null}
          {otherGrammar.length > 0 && (
          <div aria-label="Grammar">
            <strong>Grammar</strong>
            <ul>
              {otherGrammar.map((item) => (
                <li key={`${item.id}-${item.start_idx}`}><span lang="ja">{item.text}</span> — {item.meaning}</li>
              ))}
            </ul>
          </div>
          )}
        </section>
        {wordToken.word_id !== null && <footer className="panel-familiarity">
          <RatingScale value={score ?? null} onChange={onChange} disabled={saving} />
          {saving && <p className="panel-save-status" role="status">Saving…</p>}
          {error && <p className="panel-save-error" role="alert">{error}</p>}
        </footer>}
      </div>
    );
  }
}

function Panel({ localJapDb, language, onFamiliarityChange }: PanelProps) {
  const [currWordId, setCurrWordId] = useState<number | null>();
  const [selectedToken, setSelectedToken] = useState<TokenGroup | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<{ wordId: number; message: string } | null>(null);
  const [currWordPosition, setCurrWordPosition] = useState<DOMRect | null>(
    null,
  );
  const [windowData, setWindowData] = useState({
    height: window.innerHeight,
    width: window.innerWidth,
  });
  const panelRef = useRef<HTMLDivElement>(null);
  const [panelData, setPanelData] = useState({
    height: 0,
    width: 0,
  });

  useLayoutEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;

    function measurePanel() {
      if (!panel) return;
      const { height, width } = panel.getBoundingClientRect();
      setPanelData((previous) =>
        previous.height === height && previous.width === width
          ? previous
          : { height, width },
      );
    }

    measurePanel();
    const observer = new ResizeObserver(measurePanel);
    observer.observe(panel);
    return () => observer.disconnect();
  }, [selectedToken]);

  useEffect(() => {
    function handleWindowResize() {
      setWindowData({ height: window.innerHeight, width: window.innerWidth });
    }

    function handleWordClick(event: Event) {
      const result = event as CustomEvent<selectionData>;
      const wordId = result.detail.wordToken.word_id;
      setCurrWordId(wordId);
      setSelectedToken(result.detail.wordToken);
      const panelData = result.detail.rect;
      setCurrWordPosition(panelData);
    }

    function handlePointerDown(event: PointerEvent) {
      const panel = panelRef.current;
      if (!panel) return;

      const clickInPanel = event.composedPath().includes(panel);

      if (!clickInPanel) {
        setCurrWordId(null);
        setSelectedToken(null);
      }
    }

    function handleKeyPress(event: globalThis.KeyboardEvent) {
      if (event.key == "Escape") {
        setCurrWordId(null);
        setSelectedToken(null);
      }
    }

    window.addEventListener("resize", handleWindowResize);
    document.addEventListener("vocab-word-click", handleWordClick);
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyPress);

    return () => {
      window.removeEventListener("resize", handleWindowResize);
      document.removeEventListener("vocab-word-click", handleWordClick);
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyPress);
    };
  }, [localJapDb]);

  if (!selectedToken || !currWordPosition) {
    return null;
  } else {
    const storedWord = currWordId != null ? localJapDb[currWordId] : undefined;
    const word = selectedToken && storedWord
      ? { ...selectedToken, familiarity_score: storedWord.familiarity_score }
      : selectedToken;
    if (word)
      return panelContent(
        word,
        currWordPosition,
        panelData,
        windowData,
        panelRef,
        (score) => {
          if (saving || currWordId == null) return;
          const wordId = currWordId;
          setSaving(true);
          setSaveError(null);
          void onFamiliarityChange(wordId, score)
            .catch(() => setSaveError({ wordId, message: "Could not save this word. Please try again." }))
            .finally(() => setSaving(false));
        },
        language,
        saving,
        saveError && saveError.wordId === currWordId ? saveError.message : "",
      );
  }
}

export default Panel;
