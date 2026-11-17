"""Honorifics and person-name tags must not receive unrelated word glosses."""

import pytest

from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseReading, JapaneseSpelling
from app.services.japanese_vocab.grouping import add_db_data_to_tokens, regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text
from test_batch_word_lookup import dictionary_session


@pytest.fixture
def name_dictionary(dictionary_session):
    session, _ = dictionary_session
    for word_id, spelling, reading, gloss in [
        (101, "平田", "ひらた", "rice field on flat land"),
        (102, "金", "きん", "gold"),
    ]:
        session.add(JapaneseDictionary(
            word_id=word_id, source_entry_id=1000 + word_id,
            senses=[{"pos": ["noun (common) (futsuumeishi)"], "glosses": [gloss]}],
            spellings=[JapaneseSpelling(spelling=spelling, position=0, info=[], priorities=[])],
            readings=[JapaneseReading(reading=reading, position=0, info=[], priorities=[],
                                      no_kanji=False, restricted_spellings=[])],
        ))
    session.commit()
    return session


@pytest.mark.parametrize("sentence,surface", [
    ("平田さんは来た。", "平田さん"),
    ("金さんは来た。", "金さん"),
    ("田中さんと話した。", "田中さん"),
])
def test_person_name_is_clickable_without_dictionary_sense(name_dictionary, sentence, surface):
    groups = regroup_tokens(sentence, parse_japanese_text(sentence))
    group = next(group for group in add_db_data_to_tokens(name_dictionary, groups, 1)
                 if group.text == surface)
    assert group.display is True
    assert group.word_id is None
    assert group.senses is None
    assert group.grammar[0].id == "person_name"
    assert sentence[group.start_idx:group.end_idx] == surface


@pytest.mark.parametrize("sentence", ["金", "金がない。", "金が高い。"])
def test_ordinary_gold_remains_a_dictionary_word(name_dictionary, sentence):
    groups = regroup_tokens(sentence, parse_japanese_text(sentence))
    group = next(group for group in add_db_data_to_tokens(name_dictionary, groups, 1)
                 if group.text == "金")
    assert group.word_id == 102
    assert group.senses[0]["glosses"] == ["gold"]
    assert all(item.id != "person_name" for item in group.grammar)
