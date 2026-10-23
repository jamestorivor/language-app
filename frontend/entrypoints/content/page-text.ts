import type { selectionData } from "./shadow_root_components/Panel";

// These types also in background.ts might be better to have a file for all schemas
type ParseJapaneseMessage = {
  type: "PARSE_JAPANESE";
  text: string;
};
const PARSE_JAPANESE_MESSAGE_TYPE = "PARSE_JAPANESE";

type JapaneseToken = {
  text: string;
  dictionary_form: string;
  katakana_reading: string;
  start_idx: number;
  end_idx: number;
};

type ParseJapaneseResponse =
  | { ok: true; tokens: JapaneseToken[] }
  | { ok: false; error: string };

async function parsePageOnLoad() {
  const pageText: string | null = document.body.innerText;
  if (!pageText) {
    return null;
  }

  const selectedText: string = pageText.trim();
  if (selectedText.length < 1) {
    return null;
  }

  let response: ParseJapaneseResponse;
  try {
    response = await browser.runtime.sendMessage({
      type: PARSE_JAPANESE_MESSAGE_TYPE,
      text: pageText,
    });
    if (response.ok) {
      console.log(response.tokens);
      return response.tokens;
    } else if (!response.ok) {
      throw new Error(response.error);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(message);
  }
}

function handleTextSelection(): selectionData | null {
  const selection: Selection | null = window.getSelection();
  if (!selection) {
    return null;
  }

  const selectedText: string = selection.toString().trim();
  if (selectedText.length < 1) {
    return null;
  }
  const range = selection.getRangeAt(0);
  const rect = range.getBoundingClientRect();
  return {
    selectedText: selectedText,
    rect: rect,
  };
}

export { handleTextSelection, parsePageOnLoad };
