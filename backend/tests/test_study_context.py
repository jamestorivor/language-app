"""Study source snapshots never enroll cards and never invent timestamps."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.data_access.podcast import _transcript_data, rebuild_chunks
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseWordFamiliarity
from app.db.models.podcast import PodcastChunk, PodcastEpisode, PodcastTranscript, PodcastVocabularyAnalysis, PodcastVocabularyBaseline
from app.db.models.study import StudyCard, StudyMembership, StudyReview, VocabularyOccurrence, WordStudyFamiliarity, WordStudyReview, WordStudySchedule
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.services.podcast.external_transcript import parse_external_transcript
from app.services.podcast.study_context import cue_time


@compiles(JSONB, "sqlite")
def _jsonb_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
def context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    for model in (User, JapaneseDictionary, JapaneseWordFamiliarity, PodcastEpisode, PodcastChunk,
                  PodcastTranscript, PodcastVocabularyAnalysis, PodcastVocabularyBaseline, StudyCard,
                  StudyReview, StudyMembership, WordStudyFamiliarity, WordStudySchedule,
                  VocabularyOccurrence, WordStudyReview):
        model.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as db:
        db.add(User(id=1, name="test"))
        db.add(JapaneseDictionary(word_id=7, source_entry_id=7, senses=[{"glosses": ["cat"]}]))
        db.flush()
        db.add_all([PodcastEpisode(id=10, user_id=1, title="First", author="A", audio_location="one", duration=60, language="ja"),
                    PodcastEpisode(id=20, user_id=1, title="Second", author="B", audio_location="two", duration=60, language="ja")])
        db.flush()
        first, cues = _transcript_data([{"start": 12.5, "duration": 2.2, "text": "猫と猫がいます。"}])
        second, cues2 = _transcript_data([{"start": 7, "duration": 1.5, "text": "猫です。"}])
        db.add_all([PodcastChunk(id=11, user_id=1, podcast_id=10, start_time=0, end_time=60,
                                 transcript=PodcastTranscript(text=first, cues=cues)),
                    PodcastChunk(id=21, user_id=1, podcast_id=20, start_time=0, end_time=60,
                                 transcript=PodcastTranscript(text=second, cues=cues2))])
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                yield client, db
        finally:
            app.dependency_overrides.clear()
    engine.dispose()


def _add(client, *, second=False):
    request = ({"word_id": 7, "segment_id": 21, "sentence_start": 0, "sentence_end": 4,
                "target_start": 0, "target_end": 1, "target_text": "猫", "sentence": "猫です。"}
               if second else
               {"word_id": 7, "segment_id": 11, "sentence_start": 0, "sentence_end": 8,
                "target_start": 2, "target_end": 3, "target_text": "猫", "sentence": "猫と猫がいます。"})
    request.update(dictionary_form="猫", reading="ねこ")
    result = client.post("/api/study/cards", json=request)
    assert result.status_code == 200, result.text
    return result.json()


def test_sources_keep_exact_target_offsets_and_multiple_episodes_after_removal(context):
    client, db = context
    first = _add(client)
    second = _add(client, second=True)
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 5}).status_code == 200
    assert client.delete(f"/api/study/cards/{first['id']}").status_code == 204
    assert client.get("/api/study/cards?due_only=true").json() == []
    sources = client.get(f"/api/study/cards/{first['id']}/sources").json()
    assert len(sources) == 2
    source = sources[0]
    assert source["card_id"] == first["id"] and source["episode_id"] == 10
    assert source["dictionary_form"] == "猫" and source["target_text"] == "猫"
    assert (source["target_start"], source["target_end"]) == (2, 3)
    assert (source["transcript_start"], source["transcript_end"]) == (0, 8)
    assert (source["start_ms"], source["end_ms"]) == (12500, 14700)
    assert source["timing"] == "cue" and source["source_status"] == "available"
    assert sources[1]["card_id"] == second["id"] and sources[1]["episode_id"] == 20
    cards = client.get("/api/study/cards?include_removed=true").json()
    assert {card["id"]: card["membership_active"] for card in cards} == {first["id"]: False, second["id"]: True}
    assert len(db.scalars(select(StudyCard)).all()) == 2
    assert len(db.scalars(select(StudyMembership)).all()) == 2


def test_rebuilt_segments_relocate_only_verified_sentence_and_preserve_snapshot(context):
    client, db = context
    card = _add(client)
    rebuild_chunks(db, db.get(PodcastEpisode, 10), 10, [{"start": 12.5, "duration": 2.2, "text": "猫と猫がいます。"}])
    db.commit()
    db.expire_all()
    source = client.get(f"/api/study/cards/{card['id']}/sources").json()[0]
    assert source["source_status"] == "available"
    assert source["segment_id"] != 11
    assert (source["transcript_start"], source["transcript_end"]) == (0, 8)
    assert source["start_ms"] == 12500
    segment = client.get(f"/api/podcasts/chunks/{source['segment_id']}").json()
    assert segment["transcript"]["cues"][0]["start_ms"] == 12500
    assert len(db.scalars(select(StudyCard)).all()) == 1


def test_edited_or_deleted_transcript_is_not_highlighted_as_old_source(context):
    client, db = context
    card = _add(client)
    updated = client.put("/api/podcasts/chunks/11/transcript", json={"text": "犬がいます。"})
    assert updated.status_code == 200
    source = client.get(f"/api/study/cards/{card['id']}/sources").json()[0]
    assert source["source_status"] == "changed"
    assert source["sentence"] == "猫と猫がいます。"
    assert source["transcript_start"] is None and source["transcript_end"] is None
    assert source["start_ms"] == 12500
    assert source["segment_id"] == 11
    assert len(db.scalars(select(StudyCard)).all()) == 1


def test_untimed_transcript_and_legacy_sources_never_get_synthetic_timestamp(context):
    client, db = context
    snippets = parse_external_transcript("猫と猫がいます。", 60)
    text, cues = _transcript_data(snippets)
    assert text == "猫と猫がいます。" and cues == []
    transcript = db.get(PodcastTranscript, db.scalar(select(PodcastTranscript.id).where(PodcastTranscript.podcast_chunk_id == 11)))
    transcript.cues = []
    db.commit()
    card = _add(client)
    source = client.get(f"/api/study/cards/{card['id']}/sources").json()[0]
    assert source["source_status"] == "available" and source["timing"] == "unknown"
    assert source["start_ms"] is None and source["end_ms"] is None


def test_timed_subtitle_end_is_retained_and_looking_does_not_enroll(context):
    client, db = context
    snippets = parse_external_transcript("1\n00:00:12,500 --> 00:00:14,700\n猫です。", 60, file_format="srt")
    text, cues = _transcript_data(snippets)
    assert text == "猫です。" and (cues[0]["start_ms"], cues[0]["end_ms"]) == (12500, 14700)
    assert client.get("/api/podcasts/chunks/11").status_code == 200
    assert db.scalars(select(StudyCard)).all() == []
    assert db.scalars(select(StudyMembership)).all() == []


def test_sentence_spanning_cues_uses_first_start_and_last_end(context):
    client, db = context
    transcript = db.scalar(select(PodcastTranscript).where(PodcastTranscript.podcast_chunk_id == 11))
    transcript.text, transcript.cues = _transcript_data([
        {"start": 12, "duration": 2, "text": "猫と"},
        {"start": 14.5, "duration": 1.25, "text": "猫がいます。"},
    ])
    db.commit()
    payload = {"word_id": 7, "segment_id": 11, "sentence_start": 0, "sentence_end": 9,
               "target_start": 3, "target_end": 4, "target_text": "猫", "sentence": "猫と 猫がいます。"}
    card = client.post("/api/study/cards", json=payload)
    assert card.status_code == 200, card.text
    source = client.get(f"/api/study/cards/{card.json()['id']}/sources").json()[0]
    assert (source["start_ms"], source["end_ms"]) == (12000, 15750)
    assert source["source_status"] == "available"


def test_partial_cues_never_invent_the_sentence_end():
    text, cues = _transcript_data([
        {"start": 12, "duration": 2, "text": "猫と"},
        {"start": 14, "timed": False, "text": "犬と"},
        {"start": 15, "duration": 1, "text": "鳥。"},
    ])
    assert cue_time(cues, 0, len(text)) == (12000, None)


def test_changed_cue_time_is_not_reported_as_verified(context):
    client, db = context
    card = _add(client)
    transcript = db.scalar(select(PodcastTranscript).where(PodcastTranscript.podcast_chunk_id == 11))
    transcript.text, transcript.cues = _transcript_data([
        {"start": 12.5, "duration": 9, "text": "猫と猫がいます。"},
    ])
    db.commit()
    source = client.get(f"/api/study/cards/{card['id']}/sources").json()[0]
    assert source["source_status"] == "changed"
    assert source["transcript_start"] is None


def test_source_lookup_is_user_scoped_even_after_removal(context, monkeypatch):
    client, db = context
    db.add(User(id=2, name="another user"))
    db.commit()
    card = _add(client)
    assert client.delete(f"/api/study/cards/{card['id']}").status_code == 204
    monkeypatch.setattr("app.api.study.DEVELOPMENT_USER_ID", 2)
    assert client.get(f"/api/study/cards/{card['id']}/sources").status_code == 404
    assert client.get("/api/study/cards?include_removed=true").json() == []


def test_episode_deletion_keeps_card_snapshot_without_dead_link(context):
    client, _ = context
    card = _add(client)
    assert client.delete("/api/podcasts/10").status_code == 204
    source = client.get(f"/api/study/cards/{card['id']}/sources").json()[0]
    assert source["source_status"] == "missing" and source["episode_id"] is None
    assert source["sentence"] == "猫と猫がいます。" and source["target_text"] == "猫"


def test_context_migration_refuses_to_discard_new_source_data():
    import importlib.util
    import os
    from pathlib import Path
    from uuid import uuid4
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text

    path = Path(__file__).resolve().parents[1] / "alembic/versions/a9c7e2f40b33_transcript_context.py"
    spec = importlib.util.spec_from_file_location("transcript_context_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    postgres_url = os.getenv("TEST_POSTGRES_URL")
    engine = create_engine(postgres_url or "sqlite://")
    with engine.begin() as connection:
        if postgres_url:
            schema = "test_context_" + uuid4().hex
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        connection.execute(text("CREATE TABLE podcast_transcript (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE study_cards (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO podcast_transcript (id) VALUES (1)"))
        connection.execute(text("INSERT INTO study_cards (id) VALUES (1)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            connection.execute(text("UPDATE podcast_transcript SET cues = :cues"), {"cues": '[{"start_ms": 100}]'})
            with pytest.raises(RuntimeError, match="cue timing"):
                migration.downgrade()
            connection.execute(text("UPDATE podcast_transcript SET cues = '[]'"))
            connection.execute(text("UPDATE study_cards SET dictionary_form = '猫'"))
            with pytest.raises(RuntimeError, match="dictionary forms"):
                migration.downgrade()
            connection.execute(text("UPDATE study_cards SET dictionary_form = NULL"))
            migration.downgrade()
        if postgres_url:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()
