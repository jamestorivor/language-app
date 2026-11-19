import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine, event
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.data_access.japanese_vocab import get_word_details, get_word_details_batch
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseReading, JapaneseSpelling, JapaneseWordFamiliarity
from app.db.models.user import User
from app.db.models.study import WordStudyFamiliarity
from app.db.session import get_db
from app.main import app
from app.services.japanese_vocab.grouping import regroup_tokens
from app.services.japanese_vocab.parser import parse_japanese_text


@pytest.fixture
def dictionary_session():
    models = (User, JapaneseDictionary, JapaneseSpelling, JapaneseReading, JapaneseWordFamiliarity)
    changed_types = []
    for model in models:
        for column in model.__table__.columns:
            if isinstance(column.type, (ARRAY, JSONB)):
                changed_types.append((column, column.type))
                column.type = JSON()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    try:
        for model in models:
            model.__table__.create(engine)
        WordStudyFamiliarity.__table__.create(engine)
        with Session(engine) as session:
            session.add(User(id=1, name="Test"))
            session.add_all([
                JapaneseDictionary(word_id=1, source_entry_id=101, senses=[{"pos": ["noun"], "glosses": ["cat"]}],
                    spellings=[JapaneseSpelling(spelling="猫", position=0, info=[], priorities=[])],
                    readings=[JapaneseReading(reading="ねこ", position=0, info=[], priorities=[], no_kanji=False, restricted_spellings=[])]),
                JapaneseDictionary(word_id=2, source_entry_id=1375610, senses=[{"pos": ["Godan verb with 'ru' ending"]}],
                    spellings=[JapaneseSpelling(spelling="成る", position=0, info=[], priorities=[])],
                    readings=[JapaneseReading(reading="なる", position=0, info=[], priorities=[], no_kanji=False, restricted_spellings=[])]),
                JapaneseDictionary(word_id=3, source_entry_id=1591050, senses=[{"pos": ["expressions (phrases, clauses, etc.)"]}]),
                JapaneseWordFamiliarity(user_id=1, word_id=1, familiarity_score=3),
            ])
            session.commit()
            yield session, engine
    finally:
        engine.dispose()
        for column, original in changed_types:
            column.type = original


def group(text):
    return regroup_tokens(text, parse_japanese_text(text))[0]


def test_batch_preserves_individual_lookup_results_and_reduces_queries(dictionary_session):
    session, engine = dictionary_session
    groups = [group("猫"), group("なって"), group("気がつく"), group("猫"), group("未登録語")]
    queries = []
    event.listen(engine, "before_cursor_execute", lambda *_: queries.append(1))
    expected = [get_word_details(session, token, 1) for token in groups]
    old_query_count = len(queries)
    queries.clear()
    actual = get_word_details_batch(session, groups, 1)
    assert actual == expected
    assert [result.word_id if result else None for result in actual[:4]] == [1, 2, 3, 1]
    assert actual[0].familiarity_score == 3
    assert len(queries) < old_query_count


def test_batch_query_count_does_not_grow_for_repeated_words(dictionary_session):
    session, engine = dictionary_session
    token = group("猫")
    queries = []
    event.listen(engine, "before_cursor_execute", lambda *_: queries.append(1))
    results = get_word_details_batch(session, [token] * 100, 1)
    assert len(results) == 100
    assert all(result.word_id == 1 for result in results)
    assert len(queries) <= 4


def test_japanese_wont_learn_is_saved_and_returned_by_parse(dictionary_session):
    session, _ = dictionary_session

    def db_override():
        yield session

    app.dependency_overrides[get_db] = db_override
    try:
        with TestClient(app) as client:
            response = client.patch("/jap/update_familiarity_score", json={"word_id": 1, "new_score": -1})
            assert response.status_code == 200
            assert response.json()["new_score"] == -1
            session.expire_all()
            assert session.get(JapaneseWordFamiliarity, (1, 1)).familiarity_score == -1
            parsed = client.post("/jap/parse", json={"text": "猫"})
            assert parsed.status_code == 200
            assert parsed.json()[0]["familiarity_score"] == -1
            assert client.patch("/jap/update_familiarity_score", json={"word_id": 1, "new_score": 0}).status_code == 422
            assert client.patch("/jap/update_familiarity_score", json={"word_id": 1, "new_score": -2}).status_code == 422
    finally:
        app.dependency_overrides.clear()
