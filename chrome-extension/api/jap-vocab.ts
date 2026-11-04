import { API_BASE_URL } from "./config";
import type { UpdateFamiliarityScoreResponse } from "@/contracts/jap-vocab";

async function updateWordFamiliarity(
  word_id: number,
  new_score: number,
): Promise<UpdateFamiliarityScoreResponse> {
  const url = new URL("jap/update_familiarity_score", API_BASE_URL);
  return await fetch(url, {
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

export { updateWordFamiliarity };
