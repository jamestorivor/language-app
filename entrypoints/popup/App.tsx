import { useState, useEffect } from "react";
import "./App.css";

async function getCurrentTab() {
  const tabs = await browser.tabs.query({ currentWindow: true, active: true });
  return tabs[0];
}

function App() {
  const [displayText, setDisplayText] = useState<string>("");

  useEffect(() => {
    async function fetchSelectedText() {
      const tab = await getCurrentTab();
      const tabId = tab?.id;

      if (tabId != null) {
        const response = await browser.tabs.sendMessage(tabId, {
          type: "GET_SELECTED_TEXT",
        });
        const { success, text } = response;

        setDisplayText(text);
      }
    }
    fetchSelectedText();
  }, []);

  return (
    <>
      <div>{displayText}</div>
    </>
  );
}

export default App;
