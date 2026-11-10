import { API_BASE_URL } from "./config";
import { loggedFetch } from "./client";
import type { ParseJapaneseResponse } from "../contracts/japanese";
import type { UpdateFamiliarityScoreResponse } from "../contracts/japanese";

async function fetchJapaneseTokenGroups(
  text: string,
  language: "ja" | "en" = "ja",
): Promise<ParseJapaneseResponse> {
  const url = new URL(`${language === "en" ? "eng" : "jap"}/parse`, API_BASE_URL);
  return await loggedFetch("japanese.parse", url, {
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

async function updateWordFamiliarity(
  word_id: number,
  new_score: number,
  language: "ja" | "en" = "ja",
): Promise<UpdateFamiliarityScoreResponse> {
  const url = new URL(`${language === "en" ? "eng" : "jap"}/update_familiarity_score`, API_BASE_URL);
  return await loggedFetch("japanese.updateFamiliarity", url, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      word_id: word_id,
      new_score: new_score,
    }),
  }).then((response) => {
    if (!response.ok) {
      throw new Error(`Backend response ${response.status}`);
    }
    return response.json();
  });
}

export { fetchJapaneseTokenGroups, updateWordFamiliarity };
