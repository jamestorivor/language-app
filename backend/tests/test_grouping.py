import pytest
from app.services.japanese_vocab.grouping import (
    regroup_tokens, find_group_end, join_tokens, match_expression,
)
from app.services.japanese_vocab.parser import parse_japanese_text
from app.schemas import JapaneseTokenizedResponse, GroupToken, MajorPOS

@pytest.mark.parametrize(
    "text, expected_text",
    [
        ("本を読みます。", "読みます"),
        ("一万円を超えた。", "超えた"),
        ("本を読んだ。", "読んだ"),
        ("食べられませんでした。", "食べられませんでした"),
        ("食べたくなかった。", "食べたくなかった"),
        ("高くなかった。", "高くなかった"),
        ("食べていました。", "食べていました"),
        ("読んでしまった。", "読んでしまった"),
        ("食べておく。", "食べておく"),
        ("食べまし", "食べまし"),
        ("食べて", "食べて"),
        ("食べて いる", "食べて"),
        ("食べて猫がいる", "食べて"),
        ("超えたというニュース", "超えた"),
    ],
)
def test_find_group_end(text, expected_text):
    tokens = parse_japanese_text(text)
    start = next(
        i for i, token in enumerate(tokens)
        if token.part_of_speech[0] in {MajorPOS.VERB, MajorPOS.ADJECTIVE}
    )
    end = find_group_end(tokens, start)

    assert "".join(token.text for token in tokens[start:end]) == expected_text
    assert 0 < end <= len(tokens)

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
            ["牛丼"], id="compound-noun",
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

    new_token: GroupToken = join_tokens(
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
    new_tokens : list[GroupToken] = regroup_tokens(text, tokens)

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
        ("ほんのわずか", ["ほんの", "わずか"]),
        ("", []),
    ],
)
def test_regroup_tokens(text, expected_groups):
    tokens : list[JapaneseTokenizedResponse] = parse_japanese_text(text)
    groups : list[GroupToken] = regroup_tokens(text, tokens)

    assert [group.text for group in groups] == expected_groups


@pytest.mark.parametrize(
    "text, expected_groups",
    [
        ("あったからかもしれません。", ["あった", "から", "かもしれません", "。"]),
        ("学生かもしれません", ["学生", "かもしれません"]),
        ("かもしれません", ["かもしれません"]),
        ("かもしれなかった", ["かもしれなかった"]),
        ("かもしれませんでした", ["かもしれませんでした"]),
        ("かも知れない", ["かも知れない"]),
        ("食べるかもしれません", ["食べる", "かもしれません"]),
        ("高いかもしれない", ["高い", "かもしれない"]),
        ("食べるかもしれます。", ["食べる", "か", "も", "しれます", "。"]),
        ("かも しれません", ["か", "も", " ", "しれません"]),
    ],
)
def test_kamoshirenai_groups(text, expected_groups):
    tokens = parse_japanese_text(text)
    groups = regroup_tokens(text, tokens)

    assert [group.text for group in groups] == expected_groups
    assert "".join(group.text for group in groups) == text
    assert [token for group in groups for token in group.tokens] == tokens
    for group in groups:
        assert text[group.start_idx:group.end_idx] == group.text
        if group.text.startswith(("かもしれ", "かも知れ")):
            assert group.lookup_form == "かもしれない"


def test_kamoshirenai_rejects_incomplete_or_invalid_endings():
    tokens = parse_japanese_text("食べるかもしれません")
    # Truncated prefixes must fail without reading beyond the token list.
    for stop in range(2, len(tokens)):
        assert not match_expression(tokens[:stop], 1)
    assert not match_expression(tokens, -1)
    assert not match_expression(tokens, len(tokens))
    assert not match_expression([], 0)

    invalid = parse_japanese_text("食べるかもしれます。")
    assert not match_expression(invalid, 1)


@pytest.mark.parametrize(
    "text, expected_lookup",
    [
        ("食べてくる", "食べる"),
        ("持って来た", "持つ"),
        ("食べておきました", "食べる"),
        ("読んでみた", "読む"),
        ("歩いていく", "歩く"),
        ("持っていった", "持つ"),
        ("食べてしまう", "食べる"),
        ("食べてもらう", "食べる"),
        ("見てあげる", "見る"),
        ("見てくれる", "見る"),
        ("見てください", "見る"),
        ("食べてみてください", "食べる"),
        ("行ってきます", "行く"),
    ],
)
def test_te_form_supporting_verbs_group_with_main_verb(text, expected_lookup):
    tokens = parse_japanese_text(text)
    groups = regroup_tokens(text, tokens)
    assert len(groups) == 1
    assert groups[0].text == text
    assert groups[0].lookup_form == expected_lookup
    assert groups[0].tokens == tokens


@pytest.mark.parametrize("text", ["食べて寝る", "食べて くる", "食べて猫を見る"])
def test_te_form_does_not_bridge_unrelated_or_nonadjacent_words(text):
    groups = regroup_tokens(text, parse_japanese_text(text))
    assert groups[0].text == "食べて"


@pytest.mark.parametrize(
    "text, expected_groups",
    [
        ("食べて", [("食べて", "食べる")]),
        ("読んで", [("読んで", "読む")]),
        ("高くて", [("高くて", "高い")]),
        ("食べなくて", [("食べなくて", "食べる")]),
        ("食べたくなくて", [("食べたくなくて", "食べる")]),
        ("食べていました", [("食べていました", "食べる")]),
        ("読んでしまって", [("読んでしまって", "読む")]),
        ("食べておく", [("食べておく", "食べる")]),
        ("食べてほしい", [("食べて", "食べる"), ("ほしい", "ほしい")]),
        ("食べて寝る", [("食べて", "食べる"), ("寝る", "寝る")]),
        ("食べて いる", [("食べて", "食べる"), (" ", " "), ("いる", "いる")]),
        ("食べ て", [("食べ", "食べる"), (" ", " "), ("て", "て")]),
        ("公園で遊ぶ", [("公園", "公園"), ("で", "で"), ("遊ぶ", "遊ぶ")]),
        ("学生で", [("学生", "学生"), ("で", "だ")]),
        ("という", [("と", "と"), ("いう", "いう")]),
        ("欠かせません", [("欠かせません", "欠かせる")]),
        ("ふっと", [("ふっと", "ふっと")]),
        ("ふっと、", [("ふっと", "ふっと"), ("、", "、")]),
        ("ふっ と", [("ふっ", "ふっ"), (" ", " "), ("と", "と")]),
        ("ゆっくりと", [("ゆっくり", "ゆっくり"), ("と", "と")]),
    ],
)
def test_te_form_and_futto_groups_preserve_lookup_and_spans(text, expected_groups):
    tokens = parse_japanese_text(text)
    groups = regroup_tokens(text, tokens)

    assert [(group.text, group.lookup_form) for group in groups] == expected_groups
    assert "".join(group.text for group in groups) == text
    assert [token for group in groups for token in group.tokens] == tokens
    for group in groups:
        assert text[group.start_idx:group.end_idx] == group.text


@pytest.mark.parametrize("text, grammar_id", [
    ("行きたくない", "negative_desire"),
    ("できなくて", "negative"),
    ("聞いてない", "negative"),
    ("起きない", "negative"),
    ("買わない", "negative"),
    ("読みませんでした", "negative"),
    ("行きたい", "desire"),
    ("人たち", "plural"),
    ("捉え方", "way_of"),
    ("分かりやすい", "easy_to"),
    ("分かりやすくない", "negative"),
])
def test_inflection_and_productive_suffix_grammar(text, grammar_id):
    groups = regroup_tokens(text, parse_japanese_text(text))
    assert len(groups) == 1
    assert groups[0].text == text
    annotation = next(item for item in groups[0].grammar if item.id == grammar_id)
    assert text[annotation.start_idx:annotation.end_idx] == annotation.text == text


@pytest.mark.parametrize("text", ["行く", "読んでみた", "かもしれない"])
def test_positive_or_lexical_negative_is_not_mislabelled(text):
    groups = regroup_tokens(text, parse_japanese_text(text))
    assert not any(item.id in {"negative", "negative_desire"} for group in groups for item in group.grammar)


@pytest.mark.parametrize("text, surface, grammar_id", [
    ("公園で遊ぶ", "で", "particle_で"),
    ("彼のために", "ため", "tame"),
    ("するために", "ため", "tame"),
    ("本では", "では", "dewa"),
    ("これとは違う", "とは", "towa"),
    ("というのは難しい", "というのは", "to_iu_no_wa"),
    ("到着したところ", "ところ", "tokoro"),
    ("ないし", "ないし", "naishi"),
    ("本とかで", "とかで", "toka_de"),
    ("本とかで読んだ", "とかで", "toka_de"),
])
def test_function_word_constructs_are_displayable_without_a_lexeme(text, surface, grammar_id, monkeypatch):
    from app.schemas import ParseJapaneseResponse
    from app.services.japanese_vocab.grouping import add_db_data_to_tokens

    monkeypatch.setattr("app.services.japanese_vocab.grouping.get_word_details_batch",
                        lambda db, tokens, user_id: [ParseJapaneseResponse(word_id=42, familiarity_score=0,
                            senses=[{"glosses": ["wrong homophone"]}]) for _ in tokens])
    groups = add_db_data_to_tokens(None, regroup_tokens(text, parse_japanese_text(text)), 1)
    group = next(g for g in groups if g.text == surface)
    assert group.display and group.word_id is None and group.senses is None
    assert [item.id for item in group.grammar] == [grammar_id]
    assert text[group.start_idx:group.end_idx] == surface


def test_suru_construction_keeps_the_verb_and_ongoing_form():
    text = "仕事をしている"
    groups = regroup_tokens(text, parse_japanese_text(text))
    verb = next(group for group in groups if group.lookup_form == "する")
    assert verb.text == "している" and not verb._grammar_only
    construction = next(item for item in verb.grammar if item.id == "wo_shite")
    assert text[construction.start_idx:construction.end_idx] == construction.text == "をして"


def test_te_ending_is_described_as_connective_grammar():
    group = regroup_tokens("食べて寝る", parse_japanese_text("食べて寝る"))[0]
    assert group.text == "食べて"
    assert [(item.id, item.text) for item in group.grammar] == [("te_form", "て")]


@pytest.mark.parametrize("text, surface", [("手を洗う", "手"), ("美しいところ", "ところ")])
def test_lexical_homophones_are_not_forced_to_grammar(text, surface):
    group = next(g for g in regroup_tokens(text, parse_japanese_text(text)) if g.text == surface)
    assert not group._grammar_only

