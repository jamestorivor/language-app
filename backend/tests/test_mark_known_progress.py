import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import current_user_id
from app.db.models.english_vocab import EnglishDictionary, EnglishWordFamiliarity
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseWordFamiliarity
from app.db.models.user import User
from app.db.session import get_db
from app.main import app


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.mark.parametrize("language,levels", [("en", ["A1", "A1", "A2"]), ("ja", ["N5", "N5", "N4"])])
def test_progress_counts_current_users_word_ratings(language, levels):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    dictionary = EnglishDictionary if language == "en" else JapaneseDictionary
    progress = EnglishWordFamiliarity if language == "en" else JapaneseWordFamiliarity
    for table in (User.__table__, dictionary.__table__, progress.__table__):
        table.create(engine)
    with Session(engine) as session:
        session.add_all([User(id=1, name="one"), User(id=2, name="two")])
        words = ([dictionary(headword=f"word{i}", lookup_key=f"word{i}", meaning="meaning", cefr_level=level)
                  for i, level in enumerate(levels)] if language == "en" else
                 [dictionary(source_entry_id=i + 1, senses=[], jlpt_level=level) for i, level in enumerate(levels)])
        words.append(dictionary(headword="unlevelled", lookup_key="unlevelled", meaning="meaning") if language == "en"
                     else dictionary(source_entry_id=4, senses=[]))
        session.add_all(words)
        session.flush()
        session.add_all([progress(user_id=1, word_id=words[0].word_id, familiarity_score=5),
                         progress(user_id=1, word_id=words[1].word_id, familiarity_score=2),
                         progress(user_id=1, word_id=words[2].word_id, familiarity_score=4),
                         progress(user_id=1, word_id=words[3].word_id, familiarity_score=5),
                         progress(user_id=2, word_id=words[1].word_id, familiarity_score=5)])
        session.commit()
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[current_user_id] = lambda: 1
        try:
            with TestClient(app) as client:
                assert client.get("/api/vocabulary/known-count", params={"language": language}).json() == {"count": 3}
                assert client.get("/api/vocabulary/known-count", params={"language": "invalid"}).status_code == 422
                response = client.get("/api/vocabulary/mark-known", params={"language": language})
                assert response.status_code == 200
                assert response.json()[:3] == [
                    {"level": levels[0], "known": 1, "total": 2},
                    {"level": levels[2], "known": 0, "total": 1},
                    {"level": "B1" if language == "en" else "N3", "known": 0, "total": 0},
                ]
                session.get(progress, (1, words[1].word_id)).familiarity_score = 5
                session.commit()
                assert client.get("/api/vocabulary/known-count", params={"language": language}).json() == {"count": 4}
                assert client.get("/api/vocabulary/mark-known", params={"language": language}).json()[0]["known"] == 2
                assert client.get("/api/vocabulary/mark-known", params={"language": "invalid"}).status_code == 422
        finally:
            app.dependency_overrides.clear()
    engine.dispose()
