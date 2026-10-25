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

type Sense = {
  glosses: string[];
  pos: string[];
  stagk: string[];
  stagr: string[];
  s_inf: string[];
};

type TokenGroup = {
  word_id: number | null;
  text: string;
  lookup_form: string;
  familiarity_score: number | null;
  senses: Sense[] | null;
  start_idx: number;
  end_idx: number;
  tokens: JapaneseToken[];
  display: boolean;
};

const PARSE_JAPANESE_MESSAGE_TYPE = "PARSE_JAPANESE";

type ParseJapaneseResponse = TokenGroup[];

export type {
  ParseJapaneseMessage,
  TokenGroup,
  JapaneseToken,
  ParseJapaneseResponse,
};

export default PARSE_JAPANESE_MESSAGE_TYPE;
