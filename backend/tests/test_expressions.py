import pytest

from app.services.japanese_vocab.grouping import regroup_tokens, add_db_data_to_tokens
from app.services.japanese_vocab.parser import parse_japanese_text
from app.data_access.japanese_vocab import get_word_id


@pytest.mark.parametrize(
    "text, surface, lookup, source_id",
    [
        ("のよう", "よう", "ようだ", 2409190),
        ("ようになる", "ようになる", "ようになる", 1013130),
        ("ようになった", "ようになった", "ようになる", 1013130),
        ("このように", "ように", "ように", 1013110),
        ("ような", "ような", "ような", 2409180),
        ("こんなふうに", "ふうに", "風", 1499730),
        ("こんな風に", "風に", "風", 1499730),
        ("ひとつ", "ひとつ", "ひとつ", 1160820),
        ("一つ", "一つ", "一つ", 1160820),
        ("ふたつ", "ふたつ", "ふたつ", 1461160),
        ("気がつく", "気がつく", "気が付く", 1591050),
        ("気が付いた", "気が付いた", "気が付く", 1591050),
        ("きがついた", "きがついた", "気が付く", 1591050),
        ("いつのまにか", "いつのまにか", "いつの間にか", 1188850),
        ("お土産", "お土産", "お土産", 1002500),
        ("おみやげ", "おみやげ", "お土産", 1002500),
        ("どうして行くの", "どうして", "どうして", 1466940),
        ("どうしても", "どうしても", "どうしても", 1466950),
    ],
)
def test_expression_groups(text, surface, lookup, source_id):
    groups = regroup_tokens(text, parse_japanese_text(text))
    group = next(group for group in groups if group.text == surface)
    assert group.lookup_form == lookup
    assert group.source_entry_id == source_id
    assert "".join(token.text for token in group.tokens) == surface
    assert text[group.start_idx:group.end_idx] == surface


@pytest.mark.parametrize("text", ["酔う", "風に吹かれる", "気 がつく", "お茶", "どうした"])
def test_expressions_do_not_capture_unrelated_text(text):
    groups = regroup_tokens(text, parse_japanese_text(text))
    assert all(group.source_entry_id is None for group in groups)


def test_expression_uses_source_entry_id_for_lookup():
    class Session:
        def scalar(self, statement):
            assert 1591050 in statement.compile().params.values()
            return 42

    group = regroup_tokens("気がつく", parse_japanese_text("気がつく"))[0]
    assert get_word_id(Session(), group) == 42


@pytest.mark.parametrize("text", ["かもしれない", "かもしれません", "かもしれなかった", "かも知れない"])
def test_kamoshirenai_is_resolved_and_displayed(text, monkeypatch):
    from app.schemas import ParseJapaneseResponse

    monkeypatch.setattr(
        "app.services.japanese_vocab.grouping.get_word_details",
        lambda db, token, user_id: ParseJapaneseResponse(
            word_id=42, familiarity_score=0,
            senses=[{"glosses": ["might"]}],
        ),
    )
    groups = regroup_tokens(text, parse_japanese_text(text))
    result = add_db_data_to_tokens(None, groups, 1)[0]
    assert result.source_entry_id == 1002970
    assert result.display is True
    assert result.senses[0]["glosses"] == ["might"]


def test_regular_particle_remains_hidden(monkeypatch):
    from app.schemas import ParseJapaneseResponse

    monkeypatch.setattr(
        "app.services.japanese_vocab.grouping.get_word_details",
        lambda db, token, user_id: ParseJapaneseResponse(
            word_id=42, familiarity_score=0, senses=[],
        ),
    )
    groups = regroup_tokens("か", parse_japanese_text("か"))
    assert add_db_data_to_tokens(None, groups, 1)[0].display is False


def test_ima_ni_natte_resolves_become_without_merging_words():
    text = "けれども今になって思うのです"
    groups = regroup_tokens(text, parse_japanese_text(text))
    assert [group.text for group in groups] == [
        "けれど", "も", "今", "に", "なって", "思う", "の", "です"
    ]
    group = next(group for group in groups if group.text == "なって")
    assert group.lookup_form == "なる"
    assert group.source_entry_id is None


def test_other_naru_contexts_do_not_force_become():
    groups = regroup_tokens("木に実がなる", parse_japanese_text("木に実がなる"))
    group = next(group for group in groups if group.text == "なる")
    assert group.source_entry_id is None
