import { useState } from "react";
import handleTextSelection from "./page-text.ts";
import "./Panel.css";

export interface selectionData {
  selectedText: string;
  rect: DOMRect;
}

function panelContent({ selectedText, rect }: selectionData) {
  return (
    <div
      style={{
        top: rect.bottom + 8,
        left: rect.left,
      }}
    >
      <p>{selectedText}</p>
      <button>Save</button>
    </div>
  );
}

function Panel() {
  const [latestSelected, setLatestSelected] = useState<selectionData | null>(
    null,
  );

  useEffect(() => {
    function handleSelectionChange() {
      const result = handleTextSelection();
      setLatestSelected(result);
    }

    document.addEventListener("selectionchange", handleSelectionChange);

    return () => {
      document.removeEventListener("selectionchange", handleSelectionChange);
    };
  }, []);

  if (!latestSelected) {
    return null;
  } else if (latestSelected) {
    return panelContent(latestSelected);
  }

  //   browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  //     if (message.type == "GET_SELECTED_TEXT") {
  //       sendResponse({ success: true, text: latestSelected?.text });
  //     }
  //   });
}

export default Panel;
