import pytest
from app.grouping import regroup_tokens, find_group_end, join_tokens
from app.parser import parse_japanese_text
from app.schemas import JapaneseTokenizedResponse, TokenGroup, MajorPOS

@pytest.mark.parametrize(
    "text, expected_length",
    [
        ("本を読みます。", 2),
        ("社会人になりました。", 3),
        ("肉を食べません。", 3),
        ("今日は行かない。", 2),
        ("昨日は行かなかった。", 3),
        ("水を飲みたい。", 2),
        ("食べませんでした", 5),
    ],
)
def test_find_group_end(text, expected_length):
    tokens : list[JapaneseTokenizedResponse] = parse_japanese_text(text)
    start_idx = None
    for i, token in enumerate(tokens):
        if token.part_of_speech[0] == MajorPOS.VERB:
            start_idx = i
            break
    assert start_idx is not None, f"No verb found in {text!r}"
    assert find_group_end(tokens, start_idx) == start_idx + expected_length

@pytest.mark.parametrize(
    (
        "original_text, start_idx, group_length, expected_text, "
        "expected_lookup, expected_span, expected_token_texts"
    ),
    [
        pytest.param(
            "読みます", 0, 2, "読みます", "読む", (0, 4),
            ["読み", "ます"], id="whole-input",
        ),
        pytest.param(
            "本を読みます。", 2, 2, "読みます", "読む", (2, 6),
            ["読み", "ます"], id="exclude-surrounding-tokens",
        ),
        pytest.param(
            "社会人になりました。", 2, 3, "なりました", "なる", (4, 9),
            ["なり", "まし", "た"], id="token-index-differs-from-character-offset",
        ),
        pytest.param(
            "読みませんでした", 0, 5, "読みませんでした", "読む", (0, 8),
            ["読み", "ませ", "ん", "でし", "た"], id="five-token-group",
        ),
        pytest.param(
            "本を読む", 2, 1, "読む", "読む", (2, 4),
            ["読む"], id="single-final-token",
        ),
        pytest.param(
            "私は牛丼です。", 2, 1, "牛丼", "牛丼", (2, 4),
            ["牛丼"], id="single-noun",
        ),
        pytest.param(
            "📚読みます。", 1, 2, "読みます", "読む", (1, 5),
            ["読み", "ます"], id="emoji-before-group",
        ),
        pytest.param(
            "\n　読みます。", 1, 2, "読みます", "読む", (2, 6),
            ["読み", "ます"], id="leading-newline-and-full-width-space",
        ),
        pytest.param(
            "読みます、飲みます。", 3, 2, "飲みます", "飲む", (5, 9),
            ["飲み", "ます"], id="second-verb-uses-its-own-lookup-form",
        ),
        pytest.param(
            "読みます。", 2, 1, "。", "。", (4, 5),
            ["。"], id="single-punctuation-token",
        ),
    ],
)
def test_join_tokens(
    original_text,
    start_idx,
    group_length,
    expected_text,
    expected_lookup,
    expected_span,
    expected_token_texts,
):
    tokens: list[JapaneseTokenizedResponse] = parse_japanese_text(original_text)
    original_tokens = [token.model_dump() for token in tokens]

    new_token: TokenGroup = join_tokens(
        original_text, tokens, start_idx, group_length
    )

    assert new_token.text == expected_text
    assert new_token.lookup_form == expected_lookup
    assert (new_token.start_idx, new_token.end_idx) == expected_span
    assert [token.text for token in new_token.tokens] == expected_token_texts
    assert new_token.tokens == tokens[start_idx:start_idx + group_length]
    assert [token.model_dump() for token in tokens] == original_tokens




def test_regroup_tokens_no_regroup():
    text = "私は牛丼です。"
    tokens = [
        JapaneseTokenizedResponse(text='私', dictionary_form='私', katakana_reading='ワタクシ', start_idx=0, end_idx=1, part_of_speech=('代名詞', '*', '*', '*', '*', '*')), 
        JapaneseTokenizedResponse(text='は', dictionary_form='は', katakana_reading='ハ', start_idx=1, end_idx=2, part_of_speech=('助詞', '係助詞', '*', '*', '*', '*')), 
        JapaneseTokenizedResponse(text='牛丼', dictionary_form='牛丼', katakana_reading='ギュウドン', start_idx=2, end_idx=4, part_of_speech=('名詞', '普通名詞', '一般', '*', '*', '*')), 
        JapaneseTokenizedResponse(text='です', dictionary_form='です', katakana_reading='デス', start_idx=4, end_idx=6, part_of_speech=('助動詞', '*', '*', '*', '助動詞-デス', '終止形-一般')), 
        JapaneseTokenizedResponse(text='。', dictionary_form='。', katakana_reading='。', start_idx=6, end_idx=7, part_of_speech=('補助記号', '句点', '*', '*', '*', '*'))
        ]  
    new_tokens : list[TokenGroup] = regroup_tokens(text, tokens)

    assert len(new_tokens) == len(tokens)
    for group, token in zip(new_tokens, tokens):
        assert group.tokens == [token]
        assert group.text == token.text
        assert group.start_idx == token.start_idx
        assert group.end_idx == token.end_idx

@pytest.mark.parametrize(
    "text, expected_groups",
    [
        ("私は牛丼です。", ["私", "は", "牛丼", "です", "。"]),
        ("本を読みます。", ["本", "を", "読みます", "。"]),
        ("社会人になりました。", ["社会人", "に", "なりました", "。"]),
        ("肉を食べません。", ["肉", "を", "食べません", "。"]),
        ("今日は行かない。", ["今日", "は", "行かない", "。"]),
        ("昨日は行かなかった。", ["昨日", "は", "行かなかった", "。"]),
        ("水を飲みたい。", ["水", "を", "飲みたい", "。"]),
        ("食べませんでした", ["食べませんでした"]),
        ("", []),
    ],
)
def test_regroup_tokens(text, expected_groups):
    tokens : list[JapaneseTokenizedResponse] = parse_japanese_text(text)
    groups : list[TokenGroup] = regroup_tokens(text, tokens)

    assert [group.text for group in groups] == expected_groups

