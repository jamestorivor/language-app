from types import SimpleNamespace

import pytest

from app.data_access.japanese_vocab import get_word_id
from app.services.japanese_vocab.ranking import RankingCandidate, rank_by_pos_and_frequency
from app.services.japanese_vocab.grouping import get_display_status, regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text


def test_prenoun_adjective_ranks_above_more_common_noun():
    garden = RankingCandidate(1, frozenset({"noun (common) (futsuumeishi)"}), frozenset({"ichi1", "news1"}))
    that = RankingCandidate(2, frozenset({"pre-noun adjectival (rentaishi)"}), frozenset({"spec1"}))
    assert rank_by_pos_and_frequency([garden, that], "連体詞")[0] == that
    coded = RankingCandidate(3, frozenset({"adj-pn"}), frozenset())
    assert rank_by_pos_and_frequency([garden, coded], "連体詞")[0] == coded


@pytest.mark.parametrize("text", ["その", "その人", "その時", "そのように"])
def test_sono_resolves_to_that_and_is_displayed(text):
    def entry(word_id, pos, priorities):
        return SimpleNamespace(
            word_id=word_id, spellings=[],
            readings=[SimpleNamespace(reading="その", priorities=priorities)],
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
        def __init__(self):
            self.calls = 0

        def scalars(self, statement):
            self.calls += 1
            entries = [] if self.calls == 1 else [
                entry(1, "noun (common) (futsuumeishi)", ["ichi1", "news1"]),
                entry(2, "pre-noun adjectival (rentaishi)", ["spec1"]),
            ]
            return Results(entries)

    group = regroup_tokens(text, parse_japanese_text(text))[0]
    assert group.text == "その"
    assert group.tokens[0].part_of_speech[0] == "連体詞"
    group.word_id = get_word_id(Session(), group)
    assert group.word_id == 2
    assert get_display_status(group) is True
