from sudachipy import Dictionary, SplitMode
from app.schemas import JapaneseTokenizedResponse

jap_dict = Dictionary(dict="core")
SPLIT_MODE = SplitMode.B

def parse_japanese_text(text: str) -> list[dict]:
    list_of_tokens = []
    tokenizer = jap_dict.tokenizer()

    tokens = tokenizer.tokenize(text, SPLIT_MODE)

    for token in tokens:
        list_of_tokens.append(
            JapaneseTokenizedResponse(
                text=token.surface(),
                dictionary_form=token.dictionary_form(),
                katakana_reading=token.reading_form(),
                start_idx=token.begin(),
                end_idx = token.end(),
                part_of_speech = token.part_of_speech()
            )
        )

    return list_of_tokens