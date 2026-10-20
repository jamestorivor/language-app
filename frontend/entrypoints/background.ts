const API_BASE_URL = import.meta.env.WXT_API_BASE_URL;

type ParseJapaneseMessage = {
  type: "PARSE_JAPANESE";
  text: string;
};

type JapaneseToken = {
  text: string;
  dictionary_form: string;
  katakana_reading: string;
  start_idx: number;
  end_idx: number;
};

const PARSE_JAPANESE_MESSAGE_TYPE = "PARSE_JAPANESE";

async function requestParseJapanese(text: string, sendResponse: Function) {
  try {
    if (typeof text !== "string") {
      sendResponse({ ok: false, error: "Text must be a string" });
      return;
    }

    const url = new URL("jap/parse", API_BASE_URL);

    await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: text,
      }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Backend response ${response.status}`);
        }

        return response.json();
      })
      .then((tokens) => sendResponse({ ok: true, tokens }));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    sendResponse({ ok: false, error: message });
  }
}

function messageListener(
  message: ParseJapaneseMessage,
  _sender: Browser.runtime.MessageSender,
  sendResponse: Function,
) {
  if (message?.type !== PARSE_JAPANESE_MESSAGE_TYPE) return;

  requestParseJapanese(message.text, sendResponse);

  return true;
}

export default defineBackground(() => {
  console.log("Hello background!", { id: browser.runtime.id });
  browser.runtime.onMessage.addListener(messageListener);
});
