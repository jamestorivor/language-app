from types import SimpleNamespace

import pytest

from app.data_access.japanese_vocab import get_word_id
from app.services.japanese_vocab.ranking import RankingCandidate, rank_by_pos_and_frequency
from app.services.japanese_vocab.grouping import regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text


def candidate(word_id, pos, priority=()):
    return RankingCandidate(word_id, frozenset(pos), frozenset(priority))


@pytest.mark.parametrize(
    "conjugation, expected",
    [("上一段-ア行", 2), ("下一段-バ行", 2), ("五段-ラ行", 1)],
)
def test_rank_verb_class_before_frequency(conjugation, expected):
    choices = [
        candidate(1, ["Godan verb with 'ru' ending"], ["ichi1"]),
        candidate(2, ["Ichidan verb"]),
    ]
    assert rank_by_pos_and_frequency(choices, "動詞", conjugation)[0].word_id == expected


def test_missing_verb_class_is_neutral_and_codes_are_supported():
    choices = [candidate(1, ["v5r"]), candidate(2, ["v1"])]
    assert rank_by_pos_and_frequency(choices, "動詞", "上一段-ア行")[0].word_id == 2
    assert rank_by_pos_and_frequency(choices, "動詞", "unknown")[0].word_id == 1
    unknown = candidate(3, ["intransitive verb"])
    assert rank_by_pos_and_frequency([unknown, choices[0]], "動詞", "上一段-ア行")[0] == unknown


def test_common_noun_with_multiple_priority_markers_breaks_tie():
    news = candidate(1, ["noun (common) (futsuumeishi)"], ["news1", "nf18"])
    direction = candidate(2, ["noun (common) (futsuumeishi)"], ["ichi1", "news1", "nf12"])
    assert rank_by_pos_and_frequency([news, direction], "名詞")[0] == direction


def test_itai_resolves_ichidan_iru_instead_of_godan_iru():
    def entry(word_id, verb_pos):
        return SimpleNamespace(
            word_id=word_id, spellings=[],
            readings=[SimpleNamespace(reading="いる", priorities=["ichi1"])],
            senses=[{"pos": [verb_pos], "stagk": [], "stagr": []}],
        )

    class Results:
        def __init__(self, entries):
            self.entries = entries

        def unique(self):
            return self

        def all(self):
            return self.entries

    class Session:
        def __init__(self):
            self.calls = 0

        def scalars(self, statement):
            self.calls += 1
            if self.calls == 1:
                return Results([])
            return Results([entry(1, "Godan verb with 'ru' ending"), entry(2, "Ichidan verb")])

    token = regroup_tokens("いたい", parse_japanese_text("いたい"))[0]
    assert get_word_id(Session(), token) == 2


def test_kimochi_no_hou_prefers_direction_over_news():
    def entry(word_id, priorities):
        return SimpleNamespace(
            word_id=word_id, spellings=[],
            readings=[SimpleNamespace(reading="ほう", priorities=priorities)],
            senses=[{"pos": ["noun (common) (futsuumeishi)"], "stagk": [], "stagr": []}],
        )

    class Results:
        def __init__(self, entries):
            self.entries = entries

        def unique(self):
            return self

        def all(self):
            return self.entries

    class Session:
        def __init__(self):
            self.calls = 0

        def scalars(self, statement):
            self.calls += 1
            entries = [] if self.calls == 1 else [
                entry(1, ["news1", "nf18"]),
                entry(2, ["ichi1", "news1", "nf12"]),
            ]
            return Results(entries)

    groups = regroup_tokens("気持ちのほう", parse_japanese_text("気持ちのほう"))
    assert get_word_id(Session(), groups[-1]) == 2
