import { useState } from "react";
import "./App.css";
import { PARSE_CURRENT_PAGE_MESSAGE_TYPE } from "@/contracts/content-messages";

async function getCurrentTab() {
  const tabs = await browser.tabs.query({ currentWindow: true, active: true });
  return tabs[0];
}

function App() {
  const [status, setStatus] = useState<string>("");

  async function parseCurrentPage() {
    setStatus("Parsing page…");
    try {
      const tab = await getCurrentTab();
      const tabId = tab?.id;

      if (tabId != null) {
        await browser.tabs.sendMessage(tabId, {
          type: PARSE_CURRENT_PAGE_MESSAGE_TYPE,
        });
        setStatus("Page parsed");
      } else {
        setStatus("No active page found");
      }
    } catch {
      setStatus("This page is not available to the extension");
    }
  }

  return (
    <main>
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
