type ParseJapaneseMessage = {
  type: "PARSE_JAPANESE";
  text: string;
};

type JapaneseToken = {
  text: string;
  dictionary_form: string;
  katakana_reading: string;
  start_idx: number;
  end_idx: number;
  part_of_speech: [string, string, string, string, string, string];
};

type TokenGroup = {
  text: string;
  lookup_form: string;
  start_idx: number;
  end_idx: number;
  tokens: JapaneseToken[];
};

type ParseJapaneseResponse =
  | { ok: true; tokens: TokenGroup[] }
  | { ok: false; error: string };

const PARSE_JAPANESE_MESSAGE_TYPE = "PARSE_JAPANESE";

export type {
  ParseJapaneseResponse,
  ParseJapaneseMessage,
  TokenGroup,
  JapaneseToken,
};

export default PARSE_JAPANESE_MESSAGE_TYPE;
