import type { MessageLayerResponse } from "@/contracts/message-types";
import PARSE_JAPANESE_MESSAGE_TYPE, {
  type TokenGroup,
} from "@/contracts/parse-japanese";

async function requestJapaneseParsing(text: string) {
  const background_response: MessageLayerResponse<TokenGroup[]> =
    await browser.runtime.sendMessage({
      type: PARSE_JAPANESE_MESSAGE_TYPE,
      text: text,
    });

  if (!background_response.ok) {
    throw new Error(background_response.error);
  }

  return background_response;
}

export { requestJapaneseParsing };
