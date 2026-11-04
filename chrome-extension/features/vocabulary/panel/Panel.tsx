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
    const senses = wordToken.senses?.slice(0, 3) ?? [];
    const score = wordToken.familiarity_score;
    const isRated = score != null && score >= 1 && score <= 5;
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
            <h2 className="panel-reading" lang="ja">
              {wordToken.lookup_form} / {reading || wordToken.text}
            </h2>
          </div>
          <div className="panel-score" aria-live="polite">
            <span
              className="panel-score-value"
              aria-label={isRated ? `Familiarity ${score} of 5` : "Unseen"}
            >
              {isRated ? (
                <>
                  {score}
                  <span className="panel-score-total"> / 5</span>
                </>
              ) : (
                "Unseen"
              )}
            </span>
          </div>
        </header>
        <section className="panel-translations" aria-label="Definitions">
          {senses.length > 0 ? (
            <ol className="panel-definition-list">
              {senses.map((sense, index) => (
                <li className="panel-definition" key={index}>
                  <span className="panel-definition-number" aria-hidden="true">
                    {index + 1}.
                  </span>
                  <p>{sense.glosses.join("; ")}</p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="panel-empty">No definitions available.</p>
          )}
        </section>
        {wordToken.grammar && wordToken.grammar.length > 0 && (
          <section className="panel-translations" aria-label="Grammar">
            <strong>Grammar</strong>
            <ul>
              {wordToken.grammar.map((item) => (
                <li key={`${item.id}-${item.start_idx}`}><span lang="ja">{item.text}</span> — {item.meaning}</li>
              ))}
            </ul>
          </section>
        )}
        <footer className="panel-familiarity">
          <RatingScale value={score ?? null} onChange={onChange} />
        </footer>
      </div>
    );
  }
}

function Panel({ localJapDb, onFamiliarityChange }: PanelProps) {
  const [currWordId, setCurrWordId] = useState<number | null>();
  const [selectedToken, setSelectedToken] = useState<TokenGroup | null>(null);
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
  }, [currWordId]);

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
      }
    }

    function handleKeyPress(event: globalThis.KeyboardEvent) {
      if (event.key == "Escape") {
        setCurrWordId(null);
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

  if (!currWordId || !currWordPosition) {
    return null;
  } else if (currWordId) {
    const storedWord = localJapDb[currWordId];
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
        (score) => onFamiliarityChange(currWordId, score),
      );
  }
}

export default Panel;
