from types import SimpleNamespace

import pytest

from app.data_access.japanese_vocab import get_word_id
from app.services.japanese_vocab.ranking import RankingCandidate, rank_by_pos_and_frequency
from app.services.japanese_vocab.grouping import get_display_status, regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text


def entry(word_id, pos, priorities, spelling=None):
    return SimpleNamespace(
        word_id=word_id,
        spellings=[SimpleNamespace(spelling=spelling, priorities=[])] if spelling else [],
        readings=[SimpleNamespace(reading="ここ", priorities=priorities, no_kanji=False, restricted_spellings=[])],
        senses=[{"pos": [pos], "stagk": [], "stagr": []}],
    )


class Results:
    def __init__(self, entries):
        self.entries = entries

    def unique(self):
        return self

    def all(self):
        return self.entries


class Session:
    def __init__(self, spelling_results, reading_results):
        self.results = iter((spelling_results, reading_results))

    def scalars(self, statement):
        return Results(next(self.results))


@pytest.mark.parametrize("text", ["ここ", "ここにいる", "ここの人"])
def test_koko_prefers_here_and_is_displayed(text):
    individual = entry(1, "noun (common) (futsuumeishi)", ["ichi1", "news1"])
    here = entry(2, "pronoun", ["ichi1"])
    group = regroup_tokens(text, parse_japanese_text(text))[0]
    assert group.tokens[0].part_of_speech[0] == "代名詞"
    group.word_id = get_word_id(Session([], [individual, here]), group)
    assert group.word_id == 2
    assert get_display_status(group)


def test_explicit_kanji_koko_remains_individual():
    individual = entry(1, "noun (common) (futsuumeishi)", ["ichi1", "news1"], "個々")
    group = regroup_tokens("個々", parse_japanese_text("個々"))[0]
    assert group.tokens[0].part_of_speech[0] == "名詞"
    assert get_word_id(Session([individual], []), group) == 1


def test_short_pronoun_pos_code():
    noun = RankingCandidate(1, frozenset({"n"}), frozenset({"ichi1", "news1"}))
    pronoun = RankingCandidate(2, frozenset({"pn"}), frozenset())
    assert rank_by_pos_and_frequency([noun, pronoun], "代名詞")[0] == pronoun
