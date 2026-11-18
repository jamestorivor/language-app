from types import SimpleNamespace

from app.services.japanese_vocab.dictionary_expressions import find_dictionary_expressions
from app.services.japanese_vocab.expressions import ExpressionRule, TokenRule, match_reviewed_expression
from app.services.japanese_vocab.grouping import find_group_end, regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text


def record(source_id, expression=False):
    return SimpleNamespace(source_entry_id=source_id, senses=[{
        "pos": ["expressions (phrases, clauses, etc.)"] if expression else ["noun (common) (futsuumeishi)"]
    }])


class Session:
    def __init__(self, spellings=None, readings=None):
        self.forms = (spellings or {}, readings or {})
        self.calls = 0

    def execute(self, statement):
        forms = self.forms[self.calls % 2]
        self.calls += 1
        values = next(iter(statement.compile().params.values()))
        return [(form, entry) for form in values for entry in forms.get(form, [])]


def test_prefix_noun_dictionary_match():
    text = "お茶"
    tokens = parse_japanese_text(text)
    matches = find_dictionary_expressions(Session({"お茶": [record(100)]}), tokens)
    group = regroup_tokens(text, tokens, matches)[0]
    assert (group.text, group.lookup_form, group.source_entry_id) == ("お茶", "お茶", 100)
    assert group.tokens == tokens


def test_dictionary_expression_matches_inflected_final_verb():
    text = "気を付けた"
    tokens = parse_japanese_text(text)
    matches = find_dictionary_expressions(Session({"気を付ける": [record(101, True)]}), tokens)
    group = regroup_tokens(text, tokens, matches)[0]
    assert (group.text, group.lookup_form, group.source_entry_id) == (text, "気を付ける", 101)
    assert group.tokens == tokens


def test_dictionary_matches_reject_ambiguous_and_non_expression_spans():
    tokens = parse_japanese_text("気を付けた")
    assert not find_dictionary_expressions(Session({"気を付ける": [record(1, True), record(2, True)]}), tokens)
    assert not find_dictionary_expressions(Session({"気を付ける": [record(1)]}), tokens)


def test_dictionary_match_does_not_cross_whitespace():
    tokens = parse_japanese_text("お 茶")
    assert not find_dictionary_expressions(Session({"お茶": [record(100)]}), tokens)


def test_reviewed_registry_picks_longest_match_regardless_of_order():
    tokens = parse_japanese_text("どうしても")
    shorter = ExpressionRule((TokenRule(surfaces=("どう",)),), "short", 1)
    longer = ExpressionRule((TokenRule(surfaces=("どう",)), TokenRule(surfaces=("し",))), "long", 2)
    assert match_reviewed_expression(tokens, 0, find_group_end, (shorter, longer)) == (2, "long", 2)


def test_grammar_annotations_overlap_main_word_without_losing_tokens():
    text = "食べてみた"
    group = regroup_tokens(text, parse_japanese_text(text))[0]
    assert group.lookup_form == "食べる"
    assert [(item.id, item.text, text[item.start_idx:item.end_idx]) for item in group.grammar] == [
        ("te_miru", "てみた", "てみた")
    ]


def test_grammar_annotations_handle_multiple_extensions_and_offsets():
    text = "本を読んでみてください。"
    group = next(group for group in regroup_tokens(text, parse_japanese_text(text)) if group.lookup_form == "読む")
    assert [item.id for item in group.grammar] == ["te_miru", "te_kudasaru"]
    assert all(text[item.start_idx:item.end_idx] == item.text for item in group.grammar)


def test_grammar_expression_is_annotated():
    group = regroup_tokens("ようになった", parse_japanese_text("ようになった"))[0]
    assert group.grammar[0].id == "you_ni_naru"


def test_parse_endpoint_uses_dictionary_matches_and_returns_grammar(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db
    from app.schemas import ParseJapaneseResponse

    db = Session({"お茶": [record(100)]})
    app.dependency_overrides[get_db] = lambda: db
    monkeypatch.setattr(
        "app.services.japanese_vocab.grouping.get_word_details_batch",
        lambda session, tokens, user_id: [ParseJapaneseResponse(word_id=1, familiarity_score=0, senses=[]) for _ in tokens],
    )
    try:
        response = TestClient(app).post("/jap/parse", json={"text": "お茶を飲んでみた"})
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 200
    groups = response.json()
    assert groups[0]["text"] == "お茶"
    verb = next(group for group in groups if group["lookup_form"] == "飲む")
    assert verb["grammar"][0]["id"] == "te_miru"
