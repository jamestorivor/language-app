import { useLayoutEffect, useState, type KeyboardEvent } from "react";
import "./Panel.css";
import getPanelPosition from "../panel-position.ts";
import RatingScale from "./RatingScale.tsx";

export interface selectionData {
  selectedText: string;
  rect: DOMRect;
}

function panelContent(
  { selectedText, rect }: selectionData,
  panelRef: React.RefObject<HTMLDivElement | null>,
  windowData: { height: number; width: number },
  panelData: { height: number; width: number },
) {
  const panelTopLeft = getPanelPosition(rect, windowData, panelData);

  if (!panelTopLeft) return;
  else if (panelTopLeft) {
    return (
      <div
        ref={panelRef}
        className="panel"
        style={{
          top: panelTopLeft.y,
          left: panelTopLeft.x,
        }}
      >
        <p>{selectedText}</p>
        <RatingScale></RatingScale>
      </div>
    );
  }
}

function Panel() {
  const [latestSelected, setLatestSelected] = useState<selectionData | null>(
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

    const { height, width } = panel.getBoundingClientRect();
    setPanelData({ height: height, width: width });
  }, [latestSelected]);

  useEffect(() => {
    function handleWindowResize() {
      setWindowData({ height: window.innerHeight, width: window.innerWidth });
    }
    function handleWordClick(event: Event) {
      const result = event as CustomEvent<selectionData>;
      setLatestSelected(result.detail);
    }
    function handlePointerDown(event: PointerEvent) {
      const panel = panelRef.current;
      if (!panel) return;

      const clickInPanel = event.composedPath().includes(panel);

      if (!clickInPanel) {
        setLatestSelected(null);
      }
    }
    function handleKeyPress(event: globalThis.KeyboardEvent) {
      if (event.key == "Escape") {
        setLatestSelected(null);
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
  }, []);

  if (!latestSelected) {
    return null;
  } else if (latestSelected) {
    return panelContent(latestSelected, panelRef, windowData, panelData);
  }
}

export default Panel;
