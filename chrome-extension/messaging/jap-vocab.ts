import { UPDATE_FAMILIARITY_SCORE_MESSAGE_TYPE } from "@/contracts/jap-vocab";
import type {
  UpdateFamiliarityScoreData,
  UpdateFamiliarityScoreResponse,
} from "@/contracts/jap-vocab";
import type { MessageLayerResponse } from "@/contracts/message-types";

async function requestWordFamiliarityUpdate(data: UpdateFamiliarityScoreData) {
  const background_response: MessageLayerResponse<UpdateFamiliarityScoreResponse> =
    await browser.runtime.sendMessage({
      type: UPDATE_FAMILIARITY_SCORE_MESSAGE_TYPE,
      data: data,
    });

  if (!background_response.ok) {
    throw new Error(background_response.error);
  }

  return background_response;
}

export { requestWordFamiliarityUpdate };
