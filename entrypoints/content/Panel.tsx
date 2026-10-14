import { useLayoutEffect, useState } from "react";
import handleTextSelection from "./page-text.ts";
import "./Panel.css";
import getPanelPosition from "./panel-position.ts";

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
        <button>Save</button>
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
    function handleSelectionChange() {
      const result = handleTextSelection();
      setLatestSelected(result);
    }
    function handleWindowResize() {
      setWindowData({ height: window.innerHeight, width: window.innerWidth });
      handleSelectionChange();
    }

    window.addEventListener("resize", handleWindowResize);
    document.addEventListener("selectionchange", handleSelectionChange);

    return () => {
      window.removeEventListener("resize", handleWindowResize);
      document.removeEventListener("selectionchange", handleSelectionChange);
    };
  }, []);

  if (!latestSelected) {
    return null;
  } else if (latestSelected) {
    return panelContent(latestSelected, panelRef, windowData, panelData);
  }

  //   browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  //     if (message.type == "GET_SELECTED_TEXT") {
  //       sendResponse({ success: true, text: latestSelected?.text });
  //     }
  //   });
}

export default Panel;
