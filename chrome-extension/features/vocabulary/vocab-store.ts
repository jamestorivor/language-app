import type { TokenGroup } from "@/contracts/parse-japanese";
import type {
  LocalJapStorage,
  UpdateFamiliarityScoreData,
  UpdateFamiliarityScoreResponse,
} from "@/contracts/jap-vocab";
import { requestWordFamiliarityUpdate } from "@/messaging/jap-vocab";

class JapaneseVocabStore {
  store: LocalJapStorage = {};

  constructor(tokenList: TokenGroup[] = []) {
    for (const token of tokenList) {
      const word_id = token.word_id;
      if (word_id !== null) {
        this.store[word_id] = token;
      }
    }
  }

  addTokens(tokenList: TokenGroup[]) {
    for (const token of tokenList) {
      const word_id = token.word_id;
      if (word_id !== null) {
        this.store[word_id] = token;
      }
    }
  }

  getTokenData(word_id: number): TokenGroup | undefined {
    return this.store[word_id];
  }

  async updateFamiliarityScore(word_id: number, new_score: number) {
    const token = this.store[word_id];
    if (token == undefined || token.word_id == null) {
      return null;
    }
    const data: UpdateFamiliarityScoreData = {
      word_id: token.word_id,
      new_score,
    };
    const response = await requestWordFamiliarityUpdate(data);
    const updateReponse: UpdateFamiliarityScoreResponse = response.response;
    token.familiarity_score = updateReponse.new_score;
    return updateReponse;
  }
}

export default JapaneseVocabStore;
