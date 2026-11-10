import type { MessageLayerResponse } from "@/contracts/message-types";
import PARSE_JAPANESE_MESSAGE_TYPE, {
  type TokenGroup,
} from "@/contracts/parse-japanese";

async function requestJapaneseParsing(text: string, language: "ja" | "en" = "ja") {
  const background_response: MessageLayerResponse<TokenGroup[]> =
    await browser.runtime.sendMessage({
      type: PARSE_JAPANESE_MESSAGE_TYPE,
      text: text,
      language,
    });

  if (!background_response.ok) {
    throw new Error(background_response.error);
  }

  return background_response;
}

export { requestJapaneseParsing };
