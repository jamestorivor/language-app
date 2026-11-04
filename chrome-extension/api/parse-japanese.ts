import { API_BASE_URL } from "./config";
import type { ParseJapaneseResponse } from "@/contracts/parse-japanese";

async function fetchJapaneseTokenGroups(
  text: string,
): Promise<ParseJapaneseResponse> {
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

export { fetchJapaneseTokenGroups };
