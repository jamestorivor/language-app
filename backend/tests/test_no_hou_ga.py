import pytest

from app.services.japanese_vocab.dictionary_expressions import find_dictionary_expressions
from app.services.japanese_vocab.grouping import get_display_status, regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text
from test_dictionary_expressions import Session, record


@pytest.mark.parametrize(
    "text, noun, expected",
    [
        ("どこか軽やかな気持ちのほうが勝っていました", "気持ち", "のほうが"),
        ("猫の方が好き", "猫", "の方が"),
        ("私のほうが早い", "私", "のほうが"),
    ],
)
def test_comparison_annotation_keeps_words_separate(text, noun, expected):
    tokens = parse_japanese_text(text)
    # Even a dictionary hit spanning the entire phrase must not hide the noun
    # or the grammar anchor from the learner.
    matches = find_dictionary_expressions(Session({noun + expected: [record(999, True)]}), tokens)
    groups = regroup_tokens(text, tokens, matches)
    assert any(group.text == noun for group in groups)
    hou = next(group for group in groups if group.text in {"ほう", "方"})
    assert len(hou.grammar) == 1
    grammar = hou.grammar[0]
    assert grammar.id == "no_hou_ga"
    assert grammar.text == expected
    assert text[grammar.start_idx:grammar.end_idx] == expected
    hou.word_id = 1
    assert get_display_status(hou)
    assert "".join(group.text for group in groups) == text


@pytest.mark.parametrize("text", ["ここから北の方へ行く", "ほう、そうですか", "気持ち の ほう が"])
def test_nonmatches_do_not_get_comparison_annotation(text):
    groups = regroup_tokens(text, parse_japanese_text(text))
    assert not any(item.id == "no_hou_ga" for group in groups for item in group.grammar)
