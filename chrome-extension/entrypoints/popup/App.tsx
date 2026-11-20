import { useState } from "react";
import { Show, SignInButton, UserButton, useAuth } from "@clerk/chrome-extension";
import "./App.css";
import { API_BASE_URL } from "@/api/config";
import { learningLanguageFromProfile } from "@/api/profile";
import { PARSE_CURRENT_PAGE_MESSAGE_TYPE } from "@/contracts/content-messages";

async function getCurrentTab() {
  const tabs = await browser.tabs.query({ currentWindow: true, active: true });
  return tabs[0];
}

function App() {
  const [status, setStatus] = useState<string>("");
  const { getToken } = useAuth();

  async function parseCurrentPage() {
    setStatus("Parsing page…");
    try {
      const token = await getToken();
      if (!token) throw new Error("Sign in to load your learning language");
      const profileResponse = await fetch(new URL("profile", API_BASE_URL), { headers: { Authorization: `Bearer ${token}` } });
      if (!profileResponse.ok) throw new Error("Could not load your learning language");
      const language = learningLanguageFromProfile(await profileResponse.json());
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
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not parse this page");
    }
  }

  return (
    <main>
      <Show when="signed-out"><p>Sign in to use your vocabulary.</p><SignInButton mode="modal" /></Show>
      <Show when="signed-in"><UserButton />
      <p>Uses the learning language in your profile.</p>
      <button
        type="button"
        onClick={parseCurrentPage}
        className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full"
      >
        Parse this page
      </button>
      {status && <p>{status}</p>}
      </Show>
    </main>
  );
}

export default App;
