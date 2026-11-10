import { useState } from "react";
import "./App.css";
import { PARSE_CURRENT_PAGE_MESSAGE_TYPE } from "@/contracts/content-messages";

async function getCurrentTab() {
  const tabs = await browser.tabs.query({ currentWindow: true, active: true });
  return tabs[0];
}

function App() {
  const [status, setStatus] = useState<string>("");
  const [language, setLanguage] = useState<"ja" | "en">("ja");

  async function parseCurrentPage() {
    setStatus("Parsing page…");
    try {
      const tab = await getCurrentTab();
      const tabId = tab?.id;

      if (tabId != null) {
        const response = await browser.tabs.sendMessage(tabId, {
          type: PARSE_CURRENT_PAGE_MESSAGE_TYPE,
          language,
        });
        setStatus(response?.ok ? "Page parsed" : response?.error ?? "Could not parse this page");
      } else {
        setStatus("No active page found");
      }
    } catch {
      setStatus("This page is not available to the extension");
    }
  }

  return (
    <main>
      <label>Language <select value={language} onChange={(event) => setLanguage(event.target.value as "ja" | "en")}>
        <option value="ja">Japanese</option>
        <option value="en">English</option>
      </select></label>
      <button
        type="button"
        onClick={parseCurrentPage}
        className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full"
      >
        Parse this page
      </button>
      {status && <p>{status}</p>}
    </main>
  );
}

export default App;
