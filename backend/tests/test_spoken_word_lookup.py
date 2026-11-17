"""Exercise disambiguation through real tokenization, grouping and DB lookup."""

import pytest

from app.data_access.japanese_vocab import get_word_details, get_word_details_batch
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseReading, JapaneseSpelling
from app.services.japanese_vocab.grouping import regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text
from test_batch_word_lookup import dictionary_session


def entry(word_id, reading, gloss, pos, *, spelling=None, priorities=()):
    return JapaneseDictionary(
        word_id=word_id,
        source_entry_id=1000 + word_id,
        senses=[{"pos": [pos], "glosses": [gloss]}],
        spellings=[JapaneseSpelling(spelling=spelling, position=0, info=[], priorities=[])] if spelling else [],
        readings=[JapaneseReading(reading=reading, position=0, info=[], priorities=list(priorities),
                                  no_kanji=False, restricted_spellings=[])],
    )


@pytest.fixture
def spoken_dictionary(dictionary_session):
    session, _ = dictionary_session
    # More frequent competing nouns make POS selection observable rather than
    # allowing a favorable database order or frequency to make the test pass.
    session.add_all([
        entry(10, "はい", "lung", "noun (common) (futsuumeishi)", spelling="肺", priorities=["news1"]),
        entry(11, "はい", "yes", "interjection (kandoushi)", priorities=["nf01"]),
        entry(9, "はい", "hello", "interjection (kandoushi)", priorities=["nf20"]),
        entry(12, "うん", "luck", "noun (common) (futsuumeishi)", spelling="運", priorities=["news1"]),
        JapaneseDictionary(word_id=13, source_entry_id=1001090,
            senses=[{"pos": ["interjection (kandoushi)"], "glosses": ["yes", "yeah", "uh huh"]}],
            readings=[JapaneseReading(reading="うん", position=0, info=[], priorities=["spec1"],
                                      no_kanji=False, restricted_spellings=[])]),
        JapaneseDictionary(word_id=14, source_entry_id=1001140,
            senses=[{"pos": ["interjection (kandoushi)"], "glosses": ["yes", "that is correct", "right"]},
                    {"pos": ["noun or verb acting prenominally"], "glosses": ["good"]}],
            readings=[JapaneseReading(reading="ええ", position=0, info=[], priorities=["ichi1"],
                                      no_kanji=False, restricted_spellings=[])]),
        JapaneseDictionary(word_id=15, source_entry_id=1012050, senses=[
            {"pos": ["adverb (fukushi)"], "s_inf": ["when urging or consoling"],
             "glosses": ['just (e.g. "just wait here")', "come now", "now, now"]},
            {"pos": ["adverb (fukushi)"], "s_inf": [],
             "glosses": ["tolerably", "passably", "moderately", "reasonably"]},
            {"pos": ["adverb (fukushi)"], "s_inf": ["when hesitating to express an opinion"],
             "glosses": ["well ...", "I think ...", "it would seem ..."]},
            {"pos": ["interjection (kandoushi)"], "s_inf": [],
             "glosses": ["oh!", "oh dear!", "wow!"]},
        ], readings=[JapaneseReading(reading="まあ", position=0, info=[], priorities=["ichi1"],
                                      no_kanji=False, restricted_spellings=[])]),
        entry(16, "ねこ", "cat", "noun (common) (futsuumeishi)", spelling="猫"),
        entry(17, "たべる", "eat", "Ichidan verb", spelling="食べる"),
        entry(18, "むかし", "old days", "noun (common) (futsuumeishi)", spelling="昔"),
    ])
    session.commit()
    return session


def groups(text):
    return regroup_tokens(text, parse_japanese_text(text))


@pytest.mark.parametrize("sentence,surface,expected", [
    ("はい、分かりました。", "はい", "yes"),
    ("うん、そうだね。", "うん", "yeah"),
    ("ええ、そうです。", "ええ", "yes"),
    ("まあ、いいでしょう。", "まあ", "well ..."),
])
def test_spoken_sentences_show_expected_primary_sense(spoken_dictionary, sentence, surface, expected):
    token = next(token for token in groups(sentence) if token.text == surface)
    single = get_word_details(spoken_dictionary, token, 1)
    batched = get_word_details_batch(spoken_dictionary, [token], 1)[0]
    assert single == batched
    assert expected in single.senses[0]["glosses"]
    assert all(gloss not in {"lung", "luck"} for sense in single.senses for gloss in sense["glosses"])
    if surface == "ええ":
        assert all("good" not in sense["glosses"] for sense in single.senses)


def test_explicit_lung_and_unambiguous_words_still_resolve(spoken_dictionary):
    tokens = [next(token for token in groups(sentence) if token.text == surface) for sentence, surface in [
        ("肺が痛い。", "肺"), ("猫が食べます。", "猫"), ("猫が食べます。", "食べます")
    ]]
    results = get_word_details_batch(spoken_dictionary, tokens, 1)
    assert [result.senses[0]["glosses"][0] for result in results] == ["lung", "cat", "eat"]
    assert [get_word_details(spoken_dictionary, token, 1) for token in tokens] == results


def test_missing_pos_match_falls_back_to_available_meaning(spoken_dictionary):
    token = next(token for token in groups("昔のこと。") if token.text == "昔")
    # Deliberately ask for an incompatible POS to simulate missing dictionary POS.
    head = token.tokens[0]
    head.part_of_speech = ("感動詞", *head.part_of_speech[1:])
    result = get_word_details(spoken_dictionary, token, 1)
    assert result is not None
    assert result.senses[0]["glosses"] == ["old days"]
    assert get_word_details_batch(spoken_dictionary, [token], 1)[0] == result


def test_missing_dictionary_form_uses_surface(spoken_dictionary):
    token = groups("猫")[0]
    token.lookup_form = "辞書にない形"
    token.tokens[0].dictionary_form = token.lookup_form
    result = get_word_details(spoken_dictionary, token, 1)
    assert result is not None
    assert result.senses[0]["glosses"] == ["cat"]
    assert get_word_details_batch(spoken_dictionary, [token], 1)[0] == result


def test_priority_tags_rank_and_keep_other_matching_entries(spoken_dictionary):
    token = groups("はい、分かりました。")[0]
    result = get_word_details(spoken_dictionary, token, 1)
    # The lower-id entry is less frequent; ordering must come from nf tags.
    assert result.word_id == 11
    assert [sense["glosses"][0] for sense in result.senses] == ["yes", "hello"]
    assert get_word_details_batch(spoken_dictionary, [token], 1)[0] == result


def test_maa_uses_hesitation_meaning_only_with_pause(spoken_dictionary):
    with_pause = groups("まあ、いいでしょう。")[0]
    without_pause = groups("まあ良い成績です。")[0]
    first, second = get_word_details_batch(spoken_dictionary, [with_pause, without_pause], 1)
    assert "well ..." in first.senses[0]["glosses"]
    assert 'just (e.g. "just wait here")' in second.senses[0]["glosses"]
