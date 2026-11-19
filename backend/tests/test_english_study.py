from sqlalchemy import select

from app.config import DEVELOPMENT_USER_ID
from app.db.models.english_vocab import EnglishDictionary, EnglishWordFamiliarity
from app.db.models.english_study import (
    EnglishStudyCard, EnglishStudyFamiliarity, EnglishStudyMembership,
    EnglishStudyOccurrence, EnglishStudyReview, EnglishStudySchedule,
)
from app.db.models.podcast import PodcastChunk, PodcastEpisode, PodcastTranscript
from test_study import setup, payload


def test_english_review_lifecycle_and_language_isolation(setup):
    client, db = setup
    engine = db.get_bind()
    for model in (EnglishDictionary, EnglishWordFamiliarity, EnglishStudyCard,
                  EnglishStudyFamiliarity, EnglishStudyMembership, EnglishStudySchedule,
                  EnglishStudyOccurrence, EnglishStudyReview):
        model.__table__.create(engine)
    db.add(EnglishDictionary(word_id=7, headword="cat", lookup_key="cat", meaning="猫 / ネコ", cefr_level="A1"))
    db.add(PodcastEpisode(id=12, user_id=DEVELOPMENT_USER_ID, audio_location="english-test", title="English", author="Test", duration=100, language="en"))
    db.flush()
    db.add(PodcastChunk(id=13, user_id=DEVELOPMENT_USER_ID, podcast_id=12, start_time=0, end_time=100))
    db.flush()
    db.add(PodcastTranscript(podcast_chunk_id=13, text="🐱 A cat sleeps. The cat eats."))
    db.commit()

    japanese = client.post("/api/study/cards", json=payload()).json()
    first = {"word_id": 7, "segment_id": 13, "sentence_start": 0, "sentence_end": 15,
             "target_start": 4, "target_end": 7, "sentence": "🐱 A cat sleeps.", "target_text": "cat"}
    second = {**first, "sentence_start": 16, "sentence_end": 29, "target_start": 20,
              "target_end": 23, "sentence": "The cat eats."}
    response = client.post("/api/study/cards", json=first)
    assert response.status_code == 200, response.text
    english = response.json()
    assert english["id"] == japanese["id"] and english["language"] == "en"
    assert english["definitions"] == ["猫", "ネコ"]
    sibling = client.post("/api/study/cards", json=second).json()
    assert client.post("/api/study/cards", json=first).json()["id"] == english["id"]
    assert len(client.get("/api/study/cards?language=en&due_only=true").json()) == 2
    assert len(client.get("/api/study/cards?due_only=true").json()) == 1
    assert client.get(f"/api/study/cards/{english['id']}/sources?language=en").json()[0]["source_status"] == "available"

    reviewed = client.post(f"/api/study/cards/{english['id']}/review?language=en", json={"rating": 3, "version": english["version"]})
    assert reviewed.status_code == 200, reviewed.text
    assert client.post(f"/api/study/cards/{english['id']}/review?language=en", json={"rating": 3, "version": english["version"]}).status_code == 409
    assert len(db.scalars(select(EnglishStudyReview)).all()) == 1
    assert client.get("/api/study/stats?language=en").json()["completed_count"] == 1

    assert client.patch("/api/eng/update_familiarity_score", json={"word_id": 7, "new_score": -1}).status_code == 200
    assert client.get("/api/study/cards?language=en&due_only=true").json() == []
    assert client.get("/api/study/cards?due_only=true").json()[0]["id"] == japanese["id"]
    assert client.patch("/api/eng/update_familiarity_score", json={"word_id": 7, "new_score": 2}).status_code == 200
    assert len(client.get("/api/study/cards?language=en&due_only=true").json()) == 1
    assert client.post("/api/vocabulary/mark-known", json={"language": "en", "level": "A1"}).status_code == 200
    assert all(c["review_status"] == "mastered" for c in client.get("/api/study/cards?language=en").json())

    card = next(c for c in client.get("/api/study/cards?language=en").json() if c["id"] == sibling["id"])
    edited = client.patch(f"/api/study/cards/{card['id']}?language=en", json={"version": card["version"], "reading": "", "definitions": ["feline"], "sentence": "The cat eats."})
    assert edited.status_code == 200
    assert edited.json()["definitions"] == ["feline"]
    assert client.delete(f"/api/study/cards/{english['id']}?language=en").status_code == 204
    assert client.post("/api/study/cards", json=first).json()["id"] == english["id"]
    assert len(db.scalars(select(EnglishStudyReview)).all()) == 1


def test_english_study_migration_creates_and_safely_removes_tables(setup):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    _, db = setup
    EnglishDictionary.__table__.create(db.get_bind())
    path = Path(__file__).resolve().parents[1] / "alembic/versions/c4e18a9d6f20_english_study.py"
    spec = importlib.util.spec_from_file_location("english_study_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    connection = db.connection()
    with Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()
        assert "english_sentence_study_schedules" in inspect(connection).get_table_names()
        migration.downgrade()
    assert "english_study_cards" not in inspect(connection).get_table_names()
