import type {
  ParseJapaneseMessage,
  ParseJapaneseResponse,
} from "@/contracts/parse-japanese";
import PARSE_JAPANESE_MESSAGE_TYPE from "@/contracts/parse-japanese";
import { fetchJapaneseTokenGroups } from "@/api/parse-japanese";

async function handleJapaneseParseRequest(
  text: string,
  sendResponse: (response: ParseJapaneseResponse) => void,
) {
  try {
    if (typeof text !== "string") {
      sendResponse({ ok: false, error: "Text must be a string" });
      return;
    }

    const response = await fetchJapaneseTokenGroups(text);

    sendResponse({ ok: true, tokens: response });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    sendResponse({ ok: false, error: message });
  }
}

function messageListener(
  message: ParseJapaneseMessage,
  _sender: Browser.runtime.MessageSender,
  sendResponse: (response: ParseJapaneseResponse) => void,
) {
  if (message?.type !== PARSE_JAPANESE_MESSAGE_TYPE) return;

  handleJapaneseParseRequest(message.text, sendResponse);

  return true;
}

export default defineBackground(() => {
  console.log("Hello background!", { id: browser.runtime.id });
  browser.runtime.onMessage.addListener(messageListener);
});
