from types import SimpleNamespace

import pytest

from app.data_access.japanese_vocab import get_word_id
from app.services.japanese_vocab.grouping import regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text


def entry(word_id, source_id, spelling, priorities):
    return SimpleNamespace(
        word_id=word_id, source_entry_id=source_id,
        spellings=[SimpleNamespace(spelling=spelling, priorities=[])],
        readings=[SimpleNamespace(reading="なる", priorities=priorities, no_kanji=False, restricted_spellings=[])],
        senses=[{"pos": ["Godan verb with 'ru' ending"], "stagk": [], "stagr": []}],
    )


class Results:
    def __init__(self, entries):
        self.entries = entries

    def unique(self):
        return self

    def all(self):
        return self.entries


class Session:
    def __init__(self, spellings, readings):
        self.results = iter((spellings, readings))

    def scalars(self, statement):
        return Results(next(self.results))


@pytest.mark.parametrize("text", ["なって", "なりました", "今になって", "大人になる"])
def test_kana_naru_defaults_to_become(text):
    fruit = entry(1, 1611000, "生る", ["ichi1", "news1"])
    become = entry(2, 1375610, "成る", ["ichi1", "news2"])
    group = next(g for g in regroup_tokens(text, parse_japanese_text(text)) if g.lookup_form == "なる")
    assert get_word_id(Session([], [fruit, become]), group) == 2


@pytest.mark.parametrize("text", ["実が生る", "実が生った"])
def test_explicit_kanji_uses_fruit_entry(text):
    fruit = entry(1, 1611000, "生る", ["ichi1", "news1"])
    group = next(g for g in regroup_tokens(text, parse_japanese_text(text)) if g.lookup_form == "生る")
    assert get_word_id(Session([fruit], []), group) == 1


def test_missing_default_falls_back_to_available_candidate():
    fruit = entry(1, 1611000, "生る", ["ichi1", "news1"])
    group = regroup_tokens("なって", parse_japanese_text("なって"))[0]
    assert get_word_id(Session([], [fruit]), group) == 1
