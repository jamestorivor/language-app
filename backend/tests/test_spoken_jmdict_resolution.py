"""Exercise spoken defaults against the actual bundled JMdict entries."""

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app.data_access.japanese_vocab import get_word_details, get_word_details_batch
from app.db.import_jap_dictionary import construct_db_objects, parse_entry
from app.db.models.japanese_vocab import JapaneseDictionary
from app.services.japanese_vocab.grouping import regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text
from test_batch_word_lookup import dictionary_session


@pytest.fixture(scope="module")
def jmdict_records():
    ids = {1157170, 1595910, 1313580, 1241450, 1631370, 1587190,
           1502390, 1322990, 1529550, 1518540, 1374550, 1190860, 1009320,
           1000420, 1000430, 1012050, 1215240, 1633990, 2069620, 1008190, 1226480}
    path = Path(__file__).resolve().parents[2] / "data" / "JMdict_e.gz"
    records = []
    with gzip.open(path, "rt", encoding="utf-8") as source:
        for _, element in ET.iterparse(source, events=("end",)):
            if element.tag != "entry":
                continue
            if int(element.findtext("ent_seq")) in ids:
                record = parse_entry(element)
                records.append(record)
            element.clear()
    assert {record["source_entry_id"] for record in records} == ids
    return records


@pytest.fixture
def actual_entries(dictionary_session, jmdict_records):
    session, _ = dictionary_session
    session.add_all(construct_db_objects(record) for record in jmdict_records)
    session.commit()
    return session


@pytest.mark.parametrize("text,expected,gloss", [
    ("する", 1157170, "to do"),
    ("こと", 1313580, "thing"),
    ("いける", 1631370, "to be good (at)"),
    ("もの", 1502390, "thing"),
    ("なくなった", 1529550, "to be lost (e.g. luggage)"),
    ("すご", 1374550, "amazing"),
    ("おかしい", 1190860, "strange"),
    ("どんどん", 1009320, "rapidly"),
    ("擦る", 1595910, "to rub"),
    ("箏", 1241450, "koto"),
    ("生ける", 1587190, "to arrange (flowers)"),
    ("者", 1322990, "person"),
    ("亡くなった", 1518540, "to die"),
])
def test_spoken_defaults_and_explicit_kanji(actual_entries, text, expected, gloss):
    token = regroup_tokens(text, parse_japanese_text(text))[0]
    result = get_word_details(actual_entries, token, 1)
    entry = actual_entries.get(JapaneseDictionary, result.word_id)
    assert entry.source_entry_id == expected
    assert any(gloss in value for value in result.senses[0]["glosses"])
    assert get_word_details_batch(actual_entries, [token], 1)[0] == result


@pytest.mark.parametrize("text,surface,source_id,gloss", [
    ("あの、聞きたい", "あの", 1000430, "um"),
    ("あの本", "あの", 1000420, "that"),
    ("ま、いいか", "ま", 1012050, "well ..."),
    ("間がある", "間", 1215240, "time"),
    ("はあ、そうですか", "はあ", 2069620, "sigh"),
])
def test_filler_selection_depends_on_pause_and_pos(actual_entries, text, surface, source_id, gloss):
    token = next(token for token in regroup_tokens(text, parse_japanese_text(text)) if token.text == surface)
    result = get_word_details(actual_entries, token, 1)
    assert actual_entries.get(JapaneseDictionary, result.word_id).source_entry_id == source_id
    assert gloss in result.senses[0]["glosses"]


@pytest.mark.parametrize("sentence,surface,source_id,is_negative", [
    ("話がつまらない。", "つまらない", 1008190, False),
    ("映画がつまらなかった。", "つまらなかった", 1008190, False),
    ("話がつまらなくて困る。", "つまらなくて", 1008190, False),
    ("管がつまらない。", "つまらない", 1226480, True),
    ("パイプがつまらなかった。", "つまらなかった", 1226480, True),
    ("管が詰まらない。", "詰まらない", 1226480, True),
])
def test_tsumaranai_uses_clausal_evidence(actual_entries, sentence, surface, source_id, is_negative):
    token = next(group for group in regroup_tokens(sentence, parse_japanese_text(sentence)) if group.text == surface)
    result = get_word_details(actual_entries, token, 1)
    assert actual_entries.get(JapaneseDictionary, result.word_id).source_entry_id == source_id
    assert any(meaning.id == "negative" for meaning in token.grammar) == is_negative
    assert get_word_details_batch(actual_entries, [token], 1)[0] == result
