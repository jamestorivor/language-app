import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app.data_access.japanese_vocab import get_word_details, get_word_details_batch
from app.db.import_jap_dictionary import construct_db_objects, parse_entry
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseReading, JapaneseSpelling
from app.services.japanese_vocab.grouping import regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text
from test_batch_word_lookup import dictionary_session


@pytest.fixture(scope="module")
def spoken_records():
    ids = {1001090, 1001140, 1010080, 1172610, 1472870}
    records = []
    path = Path(__file__).resolve().parents[2] / "data" / "JMdict_e.gz"
    with gzip.open(path, "rt", encoding="utf-8") as file:
        for _, element in ET.iterparse(file, events=("end",)):
            if element.tag != "entry":
                continue
            if int(element.findtext("ent_seq")) in ids:
                record = parse_entry(element)
                records.append(record)
            element.clear()
    assert {record["source_entry_id"] for record in records} == ids
    return records


@pytest.fixture
def spoken_dictionary(dictionary_session, spoken_records):
    session, _ = dictionary_session
    session.add_all(construct_db_objects(record) for record in spoken_records)
    # Force a kana spelling match so the reading entry must still be consulted.
    session.add(JapaneseDictionary(
        source_entry_id=99999991, senses=[{"pos": ["noun (common) (futsuumeishi)"], "glosses": ["fake noun"]}],
        spellings=[JapaneseSpelling(spelling="はい", position=0, info=[], priorities=["ichi1", "news1"])],
        readings=[JapaneseReading(reading="はい", position=0, info=[], priorities=["ichi1"],
                                  no_kanji=False, restricted_spellings=[])],
    ))
    session.commit()
    return session


@pytest.mark.parametrize("sentence,surface,source_id,gloss", [
    ("はい、分かりました。", "はい", 1010080, "yes"),
    ("うん、そうだね。", "うん", 1001090, "yes"),
    ("ええ、そうです。", "ええ", 1001140, "yes"),
    ("肺が痛い。", "肺", 1472870, "lung"),
    ("運がいい。", "運", 1172610, "fortune"),
])
def test_interjections_do_not_become_homophone_nouns(spoken_dictionary, sentence, surface, source_id, gloss):
    token = next(group for group in regroup_tokens(sentence, parse_japanese_text(sentence)) if group.text == surface)
    result = get_word_details(spoken_dictionary, token, 1)
    assert spoken_dictionary.get(JapaneseDictionary, result.word_id).source_entry_id == source_id
    assert gloss in result.senses[0]["glosses"]
    assert get_word_details_batch(spoken_dictionary, [token], 1)[0] == result


def test_interjection_sense_precedes_noun_sense(spoken_dictionary):
    token = regroup_tokens("はい、", parse_japanese_text("はい、"))[0]
    entry = spoken_dictionary.query(JapaneseDictionary).filter_by(source_entry_id=1010080).one()
    entry.senses = [
        {"pos": ["noun (common) (futsuumeishi)"], "glosses": ["noun sense"]},
        {"pos": ["interjection (kandoushi)"], "stagr": ["へい"], "glosses": ["other reading"]},
        {"pos": ["interjection (kandoushi)"], "glosses": ["yes"]},
        {"pos": [], "glosses": ["yeah"]},
    ]
    spoken_dictionary.commit()
    result = get_word_details(spoken_dictionary, token, 1)
    assert [s["glosses"][0] for s in result.senses] == ["yes", "yeah", "noun sense", "other reading"]
    assert get_word_details_batch(spoken_dictionary, [token], 1)[0] == result


def test_mixed_pos_batch_and_duplicate_spelling_reading(spoken_dictionary):
    interjection = regroup_tokens("はい、", parse_japanese_text("はい、"))[0]
    noun = interjection.model_copy(deep=True)
    noun.tokens[0].part_of_speech = ("名詞", *noun.tokens[0].part_of_speech[1:])
    yes = spoken_dictionary.query(JapaneseDictionary).filter_by(source_entry_id=1010080).one()
    yes.spellings.append(JapaneseSpelling(spelling="はい", position=0, info=[], priorities=[]))
    spoken_dictionary.commit()

    results = get_word_details_batch(spoken_dictionary, [interjection, noun], 1)
    assert [spoken_dictionary.get(JapaneseDictionary, result.word_id).source_entry_id for result in results] == [1010080, 99999991]
    assert results == [get_word_details(spoken_dictionary, token, 1) for token in (interjection, noun)]
    assert results[0].senses[0]["glosses"][0] == "yes"
