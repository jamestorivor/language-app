import type {
  ParseJapaneseMessage,
  ParseJapaneseResponse,
} from "@/contracts/parse-japanese";
import PARSE_JAPANESE_MESSAGE_TYPE from "@/contracts/parse-japanese";
import type {
  UpdateFamiliarityScoreData,
  UpdateFamiliarityScoreMessage,
  UpdateFamiliarityScoreResponse,
} from "@/contracts/jap-vocab";
import type { MessageLayerResponse } from "@/contracts/message-types";
import { UPDATE_FAMILIARITY_SCORE_MESSAGE_TYPE } from "@/contracts/jap-vocab";
import { fetchJapaneseTokenGroups } from "@/api/parse-japanese";
import { updateWordFamiliarity } from "@/api/jap-vocab";

async function handleJapaneseParseRequest(
  text: string,
  language: "ja" | "en" = "ja",
): Promise<ParseJapaneseResponse> {
  if (typeof text !== "string") {
    throw new Error("Text must be string");
  }

  return await fetchJapaneseTokenGroups(text, language);
}

async function handleFamiliarityScoreUpdateRequest(
  data: UpdateFamiliarityScoreData,
): Promise<UpdateFamiliarityScoreResponse> {
  if (
    !data ||
    !Number.isInteger(data.word_id) ||
    !Number.isInteger(data.new_score)
  ) {
    throw new Error("Invalid familiarity update data");
  }

  return await updateWordFamiliarity(data.word_id, data.new_score, data.language);
}

async function callApi<T>(
  api_call: () => Promise<T>,
): Promise<MessageLayerResponse<T>> {
  let message_response: MessageLayerResponse<T>;
  try {
    const api_response = await api_call();
    message_response = { ok: true, response: api_response };
    return message_response;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    message_response = { ok: false, error: message };
    return message_response;
  }
}

function messageListener(
  message: ParseJapaneseMessage | UpdateFamiliarityScoreMessage,
) {
  switch (message.type) {
    case PARSE_JAPANESE_MESSAGE_TYPE:
      return callApi(() => handleJapaneseParseRequest(message.text, message.language));
    case UPDATE_FAMILIARITY_SCORE_MESSAGE_TYPE:
      return callApi(() => handleFamiliarityScoreUpdateRequest(message.data));

    default:
      return undefined;
  }
}

export default defineBackground(() => {
  console.log("Hello background!", { id: browser.runtime.id });
  browser.runtime.onMessage.addListener(messageListener);
});
