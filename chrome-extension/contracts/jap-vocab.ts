import type { TokenGroup } from "./parse-japanese";

// --------------
// PROGRAM LAYER
// --------------
type LocalJapStorage = {
  [word_id: number]: TokenGroup;
};

type UpdateFamiliarityScoreData = {
  word_id: number;
  new_score: number;
  language?: "ja" | "en";
};

// --------------
// MESSAGING LAYER (program <-> background)
// --------------

const UPDATE_FAMILIARITY_SCORE_MESSAGE_TYPE = "UPDATE_FAMILIARITY_SCORE";

type UpdateFamiliarityScoreMessage = {
  type: "UPDATE_FAMILIARITY_SCORE";
  data: UpdateFamiliarityScoreData;
};

// --------------
// API LAYER (backend <-> api)
// --------------

type UpdateFamiliarityScoreResponse = {
  word_id: number;
  new_score: number;
};

export { UPDATE_FAMILIARITY_SCORE_MESSAGE_TYPE };
export type {
  LocalJapStorage,
  UpdateFamiliarityScoreData,
  UpdateFamiliarityScoreMessage,
  UpdateFamiliarityScoreResponse,
};
