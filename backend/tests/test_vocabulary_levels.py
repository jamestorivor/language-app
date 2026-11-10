import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import DEVELOPMENT_USER_ID
from app.db.import_english_dictionary import import_entries
from app.db.import_jap_dictionary import construct_db_objects
from app.db.models.english_vocab import EnglishDictionary, EnglishWordFamiliarity
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseWordFamiliarity
from app.db.models.user import User
from app.db.session import get_db
from app.db.vocabulary_levels import english_levels, japanese_levels
from app.main import app


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


def test_level_sources_and_new_dictionary_entries():
    assert japanese_levels()[1198180] == "N5"  # 会う
    assert english_levels()["apple"] == "A1"
    entry = construct_db_objects({"source_entry_id": 1198180, "spellings": [], "readings": [], "senses": []})
    assert entry.jlpt_level == "N5"
    engine = create_engine("sqlite://")
    EnglishDictionary.__table__.create(engine)
    with Session(engine) as session:
        import_entries(session, {"apple": "りんご", "not-in-level-list-xyz": "test"})
        words = session.query(EnglishDictionary).order_by(EnglishDictionary.word_id).all()
        assert [word.cefr_level for word in words] == ["A1", None]


@pytest.mark.parametrize("language,levels,threshold", [
    ("en", ["A1", "A2", "B1", None], "A2"),
    ("ja", ["N5", "N4", "N3", None], "N4"),
])
def test_mark_known_includes_threshold_and_preserves_other_words(language, levels, threshold):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    dictionary = EnglishDictionary if language == "en" else JapaneseDictionary
    progress = EnglishWordFamiliarity if language == "en" else JapaneseWordFamiliarity
    for table in (User.__table__, dictionary.__table__, progress.__table__):
        table.create(engine)
    with Session(engine) as session:
        session.add(User(id=DEVELOPMENT_USER_ID, name="test"))
        if language == "en":
            words = [dictionary(headword=f"word{i}", lookup_key=f"word{i}", meaning="meaning", cefr_level=level) for i, level in enumerate(levels)]
        else:
            words = [dictionary(source_entry_id=i + 1, senses=[], jlpt_level=level) for i, level in enumerate(levels)]
        session.add_all(words)
        session.flush()
        ids = [word.word_id for word in words]
        session.add_all([progress(user_id=DEVELOPMENT_USER_ID, word_id=ids[0], familiarity_score=2),
                         progress(user_id=DEVELOPMENT_USER_ID, word_id=ids[2], familiarity_score=3)])
        session.commit()
        app.dependency_overrides[get_db] = lambda: session
        try:
            with TestClient(app) as client:
                assert client.post("/api/vocabulary/mark-known", json={"language": language, "level": "wrong"}).status_code == 422
                for _ in range(2):
                    response = client.post("/api/vocabulary/mark-known", json={"language": language, "level": threshold})
                    assert response.status_code == 200
                    assert response.json() == {"matched_words": 2}
                session.expire_all()
                assert [session.get(progress, (DEVELOPMENT_USER_ID, word_id)).familiarity_score for word_id in ids[:3]] == [5, 5, 3]
                assert session.get(progress, (DEVELOPMENT_USER_ID, ids[3])) is None
        finally:
            app.dependency_overrides.clear()
    engine.dispose()


def test_migration_populates_existing_dictionaries():
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text

    # Alembic's versions directory is not a Python package.
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "alembic/versions/a8c15a4b71e2_vocabulary_levels.py"
    spec = importlib.util.spec_from_file_location("vocabulary_levels_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE japanese_dictionary (word_id INTEGER PRIMARY KEY, source_entry_id INTEGER)"))
        connection.execute(text("CREATE TABLE english_dictionary (word_id INTEGER PRIMARY KEY, lookup_key TEXT)"))
        connection.execute(text("INSERT INTO japanese_dictionary VALUES (1, 1198180), (2, 1)"))
        connection.execute(text("INSERT INTO english_dictionary VALUES (1, 'apple'), (2, 'not-in-level-list-xyz')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert connection.execute(text("SELECT jlpt_level FROM japanese_dictionary ORDER BY word_id")).scalars().all() == ["N5", None]
        assert connection.execute(text("SELECT cefr_level FROM english_dictionary ORDER BY word_id")).scalars().all() == ["A1", None]
