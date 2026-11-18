import gzip
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.import_jap_dictionary import construct_db_objects, parse_entry
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseReading, JapaneseSpelling, JapaneseWordFamiliarity
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.services.japanese_vocab.grouping import regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text


SENTENCE = "なんか俺そこひっくり返えんのかな?どうなんだろうって今ちょっと思ってたんだよ。"
SURFACE = "ひっくり返えん"
SOURCE_ID = 1169320


@pytest.fixture
def real_dictionary_session():
    path = Path(__file__).resolve().parents[2] / "data" / "JMdict_e.gz"
    with gzip.open(path, "rb") as source:
        for _, element in ET.iterparse(source, events=("end",)):
            if element.tag != "entry":
                continue
            if element.findtext("ent_seq") == str(SOURCE_ID):
                entry = construct_db_objects(parse_entry(element))
                break
            element.clear()
        else:
            raise AssertionError("Reviewed JMdict entry is missing")

    models = (User, JapaneseDictionary, JapaneseReading, JapaneseSpelling, JapaneseWordFamiliarity)
    changed = []
    for model in models:
        for column in model.__table__.columns:
            if isinstance(column.type, (ARRAY, JSONB)):
                changed.append((column, column.type))
                column.type = JSON()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    try:
        for model in models:
            model.__table__.create(engine)
        with Session(engine) as session:
            session.add_all([User(id=1, name="Test"), entry])
            session.commit()
            yield session, entry.word_id
    finally:
        engine.dispose()
        for column, original in changed:
            column.type = original


def test_reviewed_variant_preserves_transcript_and_following_particles():
    tokens = parse_japanese_text(SENTENCE)
    groups = regroup_tokens(SENTENCE, tokens)
    index = next(i for i, group in enumerate(groups) if group.text == SURFACE)
    group = groups[index]
    assert group.lookup_form == "ひっくり返る"
    assert group.source_entry_id == SOURCE_ID
    assert SENTENCE[group.start_idx:group.end_idx] == SURFACE
    assert [t.text for t in group.tokens] == ["ひっ", "くり", "返", "えん"]
    assert [g.text for g in groups[index + 1:index + 4]] == ["の", "か", "な"]
    assert "".join(group.text for group in groups) == SENTENCE
    assert not any("negative" in annotation.id for annotation in group.grammar)


@pytest.mark.parametrize("text", ["ひっ くり返えん", "ひっくり返る", "ひっくり返らん"])
def test_variant_rule_does_not_consume_nearby_forms(text):
    groups = regroup_tokens(text, parse_japanese_text(text))
    assert all(group.source_entry_id != SOURCE_ID for group in groups)
    assert "".join(group.text for group in groups) == text


def test_parse_and_rating_use_real_jmdict_entry(real_dictionary_session):
    session, word_id = real_dictionary_session
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            result = client.post("/jap/parse", json={"text": SENTENCE})
            assert result.status_code == 200
            variant = next(group for group in result.json() if group["text"] == SURFACE)
            assert variant["word_id"] == word_id and variant["display"] is True
            assert variant["familiarity_score"] == 0
            assert "to be overturned" in variant["senses"][0]["glosses"]

            rated = client.patch("/jap/update_familiarity_score", json={"word_id": word_id, "new_score": 3})
            assert rated.status_code == 200
            result = client.post("/jap/parse", json={"text": "ひっくり返る"})
            assert result.status_code == 200
            assert result.json()[0]["word_id"] == word_id
            assert result.json()[0]["familiarity_score"] == 3
    finally:
        app.dependency_overrides.pop(get_db, None)
