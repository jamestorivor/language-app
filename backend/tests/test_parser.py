import pytest
from app.schemas import JapaneseTokenizedResponse, MajorPOS
from app.parser import parse_japanese_text

def test_parse_japanese_text():
    tokens : list[JapaneseTokenizedResponse] = parse_japanese_text("猫が食べます。")

    assert [token.text for token in tokens] == ['猫', 'が', '食べ', 'ます', '。']
    assert tokens[2].dictionary_form == "食べる"
    assert tokens[2].part_of_speech[0] == MajorPOS.VERB

def test_japanse_space_character():
    tokens : list[JapaneseTokenizedResponse] = parse_japanese_text("　")

    assert tokens[0].text == "\u3000"
    assert tokens[0].dictionary_form == " "
    assert tokens[0].part_of_speech[0] == MajorPOS.WHITESPACE

def test_empty_text():
    tokens: list[JapaneseTokenizedResponse] = parse_japanese_text("")

    assert tokens == []

@pytest.mark.parametrize("text", [
    "猫が走る。",
    "今日はPythonを勉強する。",
    "猫 🐱",
    "  猫\n犬",
])
def test_token_positions(text):
    tokens = parse_japanese_text(text)

    for token in tokens:
        assert text[token.start_idx:token.end_idx] == token.text
