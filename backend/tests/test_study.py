from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import DEVELOPMENT_USER_ID
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseWordFamiliarity
from app.db.models.podcast import (PodcastChunk, PodcastEpisode, PodcastTranscript,
                                   PodcastVocabularyAnalysis, PodcastVocabularyBaseline)
from app.data_access.podcast import rebuild_chunks
from app.db.models.study import StudyCard, StudyReview, StudyMembership, WordStudyFamiliarity, WordStudySchedule, VocabularyOccurrence, WordStudyReview
from app.db.models.user import User
from app.db.session import get_db
from app.main import app


@compiles(JSONB, "sqlite")
def jsonb_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
def setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
    for table in (User.__table__, JapaneseDictionary.__table__, JapaneseWordFamiliarity.__table__,
                  PodcastEpisode.__table__, PodcastChunk.__table__, PodcastTranscript.__table__,
                  PodcastVocabularyBaseline.__table__, PodcastVocabularyAnalysis.__table__,
                  StudyCard.__table__, StudyReview.__table__, WordStudyFamiliarity.__table__, StudyMembership.__table__,
                  WordStudySchedule.__table__, VocabularyOccurrence.__table__, WordStudyReview.__table__):
        table.create(engine)
    with Session(engine, expire_on_commit=False) as db:
        db.add(User(id=DEVELOPMENT_USER_ID, name="test"))
        db.add(JapaneseDictionary(word_id=7, source_entry_id=1, senses=[{"glosses": ["cat"]}], jlpt_level="N5"))
        db.flush()
        db.add(PodcastEpisode(id=10, user_id=DEVELOPMENT_USER_ID, audio_location="test", title="Episode", author="Test", duration=100, language="ja"))
        db.flush()
        db.add(PodcastChunk(id=11, user_id=DEVELOPMENT_USER_ID, podcast_id=10, start_time=0, end_time=100))
        db.flush()
        db.add(PodcastTranscript(podcast_chunk_id=11, text="猫です。猫がいます。"))
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                yield client, db
        finally:
            app.dependency_overrides.clear()
    engine.dispose()


def payload(**overrides):
    return {"word_id": 7, "segment_id": 11, "sentence_start": 0, "sentence_end": 4,
            "target_start": 0, "target_end": 1, "reading": "ねこ",
            "sentence": "猫です。", "target_text": "猫", **overrides}


def test_opt_in_multiple_sentences_and_clear_only_wont_learn(setup):
    client, db = setup
    # Familiarity writes, including -1, do not create study cards.
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": -1}).status_code == 200
    assert client.get("/api/study/cards").json() == []
    first = client.post("/api/study/cards", json=payload())
    assert first.status_code == 200
    card = first.json()
    assert (card["sentence"], card["target_text"], card["definitions"]) == ("猫です。", "猫", ["cat"])
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)) is None
    # Retrying Add does not duplicate or reschedule a card, and clears -1 again.
    client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": -1})
    assert client.post("/api/study/cards", json=payload()).json()["id"] == card["id"]
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)) is None
    client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 3})
    second = client.post("/api/study/cards", json=payload(sentence_start=4, sentence_end=10, target_start=4, target_end=5, sentence="猫がいます。"))
    assert second.status_code == 200 and second.json()["id"] != card["id"]
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)).familiarity_score == 3
    assert len(client.get("/api/study/cards?segment_id=11").json()) == 2
    assert len(client.get("/api/study/cards").json()) == 2


def test_review_is_atomic_and_stale_version_rejected(setup):
    client, db = setup
    card = client.post("/api/study/cards", json=payload()).json()
    assert len(client.get("/api/study/cards?due_only=true").json()) == 1
    reviewed = client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 3, "version": 0})
    assert reviewed.status_code == 200
    assert reviewed.json()["version"] == 1
    retry = client.post("/api/study/cards", json=payload()).json()
    assert retry["version"] == 1 and retry["due_at"] == reviewed.json()["due_at"]
    assert datetime.fromisoformat(reviewed.json()["due_at"]).replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
    assert client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 3, "version": 0}).status_code == 409
    assert len(db.scalars(select(WordStudyReview)).all()) == 1
    assert client.get("/api/study/cards?due_only=true").json() == []
    assert client.delete(f"/api/study/cards/{card['id']}").status_code == 204
    assert len(db.scalars(select(WordStudyReview)).all()) == 1
    assert client.get("/api/study/cards").json() == []


def test_invalid_or_missing_context_cannot_create_card_or_clear_status(setup):
    client, db = setup
    client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": -1})
    assert client.post("/api/study/cards", json=payload(sentence_end=2, target_start=4, target_end=5)).status_code == 422
    assert client.post("/api/study/cards", json=payload(segment_id=999)).status_code == 404
    assert client.post("/api/study/cards", json=payload(sentence="犬です。" )).status_code == 409
    assert client.get("/api/study/cards").json() == []
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)).familiarity_score == -1


def test_context_survives_deleting_segment_and_episode(setup):
    client, db = setup
    card_id = client.post("/api/study/cards", json=payload()).json()["id"]
    db.delete(db.get(PodcastChunk, 11))
    db.commit()
    db.expire_all()
    card = db.get(StudyCard, card_id)
    assert card.segment_id is None and card.sentence == "猫です。"
    db.delete(db.get(PodcastEpisode, 10))
    db.commit()
    db.expire_all()
    card = db.get(StudyCard, card_id)
    assert card.episode_id is None and card.episode_title == "Episode"


def test_parse_bulk_and_transcript_updates_do_not_enroll(setup, monkeypatch):
    client, db = setup
    monkeypatch.setattr("app.api.japanese_vocab.parse_japanese_text", lambda _text: [])
    monkeypatch.setattr("app.api.japanese_vocab.find_dictionary_expressions", lambda _db, _tokens: [])
    monkeypatch.setattr("app.api.japanese_vocab.regroup_tokens", lambda *_args: [])
    monkeypatch.setattr("app.api.japanese_vocab.add_db_data_to_tokens", lambda *_args: [])
    assert client.post("/api/jap/parse", json={"text": "猫です。"}).status_code == 200
    assert client.post("/api/vocabulary/mark-known", json={"language": "ja", "level": "N5"}).status_code == 200
    assert client.put("/api/podcasts/chunks/11/transcript", json={"text": "猫です。"}).status_code == 200
    assert client.get("/api/study/cards").json() == []


def test_rebuilding_segments_keeps_card_snapshot(setup):
    client, db = setup
    card_id = client.post("/api/study/cards", json=payload()).json()["id"]
    episode = db.get(PodcastEpisode, 10)
    rebuild_chunks(db, episode, 50, [{"start": 0, "text": "猫です。"}])
    db.commit()
    db.expire_all()
    card = db.get(StudyCard, card_id)
    assert card.segment_id is None
    assert card.sentence == "猫です。"
    assert card.episode_id == 10


def test_edit_card_preserves_source_and_review_history(setup):
    client, db = setup
    card = client.post("/api/study/cards", json=payload()).json()
    edit = {"version": card["version"], "reading": "ネコ", "definitions": ["a cat", "feline"], "sentence": "猫が好きです。"}
    saved = client.patch(f"/api/study/cards/{card['id']}", json=edit)
    assert saved.status_code == 200
    assert (saved.json()["reading"], saved.json()["definitions"], saved.json()["sentence"]) == ("ネコ", ["a cat", "feline"], "猫が好きです。")
    assert saved.json()["version"] == card["version"] + 1
    source = client.get(f"/api/study/cards/{card['id']}/sources").json()[0]
    assert source["sentence"] == "猫です。" and source["source_status"] == "available"
    assert client.patch(f"/api/study/cards/{card['id']}", json=edit).status_code == 409
    assert client.get("/api/study/cards").json()[0]["sentence"] == "猫が好きです。"
    assert db.scalars(select(WordStudyReview)).all() == []
    assert client.patch(f"/api/study/cards/{card['id']}", json={**edit, "version": saved.json()["version"], "sentence": " "}).status_code == 422
