from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.import_english_dictionary import import_entries, read_entries
from app.db.models.english_vocab import EnglishDictionary, EnglishWordFamiliarity
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.services.english_vocab import _dictionary_senses, parse_english_text


def test_import_combines_variants_and_preserves_saved_word_ids(tmp_path):
    source = tmp_path / "dictionary.txt"
    source.write_text("color,colour\t色\ncolor\t彩色\n", encoding="utf-8")
    entries = read_entries(source)
    assert entries == {"color": "色\n彩色", "colour": "色"}
    engine = create_engine("sqlite://")
    for table in (User.__table__, EnglishDictionary.__table__, EnglishWordFamiliarity.__table__):
        table.create(engine)
    with Session(engine) as session:
        session.add(User(id=1, name="test"))
        assert import_entries(session, entries) == (2, 0)
        word = session.scalar(select(EnglishDictionary).where(EnglishDictionary.headword == "color"))
        word_id = word.word_id
        session.add(EnglishWordFamiliarity(user_id=1, word_id=word_id, familiarity_score=4))
        session.commit()
        assert import_entries(session, {"color": "色彩", "colour": "色"}) == (0, 1)
        session.commit()
        assert session.get(EnglishDictionary, word_id).meaning == "色彩"
        assert session.get(EnglishWordFamiliarity, (1, word_id)).familiarity_score == 4


def test_dictionary_alternatives_keep_usage_annotations():
    assert _dictionary_senses("《米》色 / 彩り\n色彩") == [
        {"glosses": ["《米》色"]}, {"glosses": ["彩り"]}, {"glosses": ["色彩"]}
    ]


def test_english_parsing_and_familiarity_endpoints():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    for table in (User.__table__, EnglishDictionary.__table__, EnglishWordFamiliarity.__table__):
        table.create(engine)
    with Session(engine) as session:
        session.add(User(id=1, name="test"))
        import_entries(session, {"go": "行く", "word": "単語", "New York": "ニューヨーク"})
        session.commit()

        def db_override():
            yield session

        app.dependency_overrides[get_db] = db_override
        try:
            with TestClient(app) as client:
                text = "🐱 She went to New York. Words!"
                response = client.post("/api/eng/parse", json={"text": text})
                assert response.status_code == 200
                groups = response.json()
                assert "".join(group["text"] for group in groups) == text
                assert all(text[group["start_idx"]:group["end_idx"]] == group["text"] for group in groups)
                by_text = {group["text"]: group for group in groups}
                assert by_text["went"]["lookup_form"] == "go"
                assert by_text["went"]["senses"][0]["glosses"] == ["行く"]
                assert by_text["New York"]["lookup_form"] == "New York"
                assert by_text["Words"]["lookup_form"] == "word"
                word_id = by_text["went"]["word_id"]
                assert client.patch("/eng/update_familiarity_score", json={"word_id": word_id, "new_score": 4}).status_code == 200
                assert client.post("/eng/parse", json={"text": "went"}).json()[0]["familiarity_score"] == 4
                assert client.patch("/eng/update_familiarity_score", json={"word_id": word_id, "new_score": 6}).status_code == 422
                assert client.patch("/eng/update_familiarity_score", json={"word_id": 99999, "new_score": 2}).status_code == 404
                assert parse_english_text(session, "", 1) == []
        finally:
            app.dependency_overrides.clear()
    engine.dispose()
