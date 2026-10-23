import type { ParseJapaneseResponse } from "@/contracts/parse-japanese";
import PARSE_JAPANESE_MESSAGE_TYPE from "@/contracts/parse-japanese";

const API_BASE_URL = import.meta.env.WXT_API_BASE_URL;

async function requestJapaneseParsing(text: string) {
  const response: ParseJapaneseResponse = await browser.runtime.sendMessage({
    type: PARSE_JAPANESE_MESSAGE_TYPE,
    text: text,
  });

  if (!response.ok) {
    throw new Error(response.error);
  }

  return response;
}

async function fetchJapaneseTokenGroups(text: string) {
  const url = new URL("jap/parse", API_BASE_URL);
  return await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text: text,
    }),
  }).then((response) => {
    if (!response.ok) {
      throw new Error(`Backend response ${response.status}`);
    }

    return response.json();
  });
}

export { requestJapaneseParsing, fetchJapaneseTokenGroups };
