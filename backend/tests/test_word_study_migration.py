"""Exercise the word-study upgrade against existing sentence cards."""
import importlib.util
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fsrs import Card, Rating, Scheduler
from sqlalchemy import MetaData, Table, create_engine, event, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

from app.db.models.user import User
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseWordFamiliarity
from app.db.models.podcast import PodcastEpisode, PodcastChunk
from app.db.models.study import StudyCard, StudyReview


@compiles(JSONB, "sqlite")
def _jsonb_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


def _migration():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/e7a4c6b09f11_word_study_schema.py"
    spec = importlib.util.spec_from_file_location("word_study_migration", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def _sentence_migration():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/f8b5d7c10a22_sentence_study_schedules.py"
    spec = importlib.util.spec_from_file_location("sentence_study_migration", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def legacy_connection():
    postgres_url = os.getenv("TEST_POSTGRES_URL")
    engine = create_engine(postgres_url or "sqlite://")

    if not postgres_url:
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as connection:
        if postgres_url:
            schema = "test_study_" + uuid4().hex
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        for table in (User.__table__, JapaneseDictionary.__table__, JapaneseWordFamiliarity.__table__,
                      PodcastEpisode.__table__, PodcastChunk.__table__, StudyCard.__table__, StudyReview.__table__):
            table.create(connection)
        # This fixture models the schema before the later transcript-context migration.
        connection.execute(text("ALTER TABLE study_cards DROP COLUMN dictionary_form"))
        # These two indexes are introduced by the migration, not the old schema.
        connection.execute(text("DROP INDEX uq_podcasts_id_user"))
        connection.execute(text("DROP INDEX uq_podcast_chunk_id_episode_user"))
        connection.execute(text("DROP INDEX uq_study_card_id_user_word"))
        connection.execute(User.__table__.insert(), [{"id": 1, "name": "one"}, {"id": 2, "name": "two"}])
        connection.execute(JapaneseDictionary.__table__.insert(), [
            {"word_id": 1, "source_entry_id": 1, "senses": []},
            {"word_id": 2, "source_entry_id": 2, "senses": []},
        ])
        connection.execute(JapaneseWordFamiliarity.__table__.insert(), [
            {"user_id": 1, "word_id": 1, "familiarity_score": 3},
            {"user_id": 1, "word_id": 2, "familiarity_score": 5},
        ])
        connection.execute(PodcastEpisode.__table__.insert(), {"id": 10, "user_id": 1, "audio_location": "url", "title": "Episode", "author": "Author", "duration": 60, "language": "ja"})
        connection.execute(PodcastChunk.__table__.insert(), {"id": 11, "user_id": 1, "podcast_id": 10, "start_time": 0, "end_time": 60})
        initial = datetime(2025, 1, 1, tzinfo=timezone.utc)
        scheduler = Scheduler(enable_fuzzing=False)
        for card_id in (1, 2):
            card = Card(card_id=card_id, due=initial)
            card, _ = scheduler.review_card(card, Rating.Good, review_datetime=initial + timedelta(days=card_id, minutes=-10))
            before = card.to_dict()
            reviewed, log = scheduler.review_card(card, Rating.Good, review_datetime=initial + timedelta(days=card_id))
            connection.execute(StudyCard.__table__.insert(), {
                "id": card_id, "user_id": 1, "word_id": 1, "occurrence_key": str(card_id),
                "episode_id": 10, "segment_id": 11, "episode_title": "Episode", "sentence": f"猫{card_id}。",
                "target_text": "猫", "reading": "ねこ", "definitions": ["cat"],
                "sentence_start": 0, "sentence_end": 3, "target_start": 0, "target_end": 1,
                "created_at": initial, "due_at": reviewed.due, "fsrs_card": reviewed.to_dict(),
                "scheduler_version": "py-fsrs-6.3.3/fsrs-6", "scheduler_config": scheduler.to_dict(), "version": 1,
            })
            connection.execute(StudyReview.__table__.insert(), {
                "id": card_id, "card_id": card_id, "rating": 3, "reviewed_at": initial + timedelta(days=card_id),
                "before_state": before, "after_state": reviewed.to_dict(), "review_log": log.to_dict(),
                "scheduler_version": "py-fsrs-6.3.3/fsrs-6",
            })
        yield connection
        if postgres_url:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


def test_migration_preserves_and_consolidates_and_empty_roundtrip(legacy_connection):
    connection = legacy_connection
    migration = _migration()
    before = connection.execute(select(JapaneseWordFamiliarity.__table__)).all()
    with Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()
        assert connection.execute(text("SELECT count(*) FROM vocabulary_study_memberships")).scalar_one() == 1
        assert connection.execute(text("SELECT word_id FROM vocabulary_study_memberships")).scalar_one() == 1
        assert connection.execute(text("SELECT legacy_card_id FROM vocabulary_study_schedules")).scalar_one() == 2
        status, due_at, eligible = connection.execute(text("SELECT review_status, next_review_at, next_eligible_at FROM vocabulary_study_schedules")).one()
        assert status == "deferred"
        def utc(value):
            if isinstance(value, str):
                value = datetime.fromisoformat(value)
            return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        assert utc(eligible) > utc(due_at)
        assert connection.execute(text("SELECT count(*) FROM legacy_sentence_card_archive")).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM vocabulary_occurrences")).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM vocabulary_study_review_logs")).scalar_one() == 2
        assert connection.execute(select(JapaneseWordFamiliarity.__table__)).all() == before
        # Existing legacy records permit a lossless downgrade if nothing changed.
        migration.downgrade()
        assert connection.execute(text("SELECT count(*) FROM study_cards")).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM study_reviews")).scalar_one() == 2


def test_downgrade_rejects_modified_study_data(legacy_connection):
    migration = _migration()
    with Operations.context(MigrationContext.configure(legacy_connection)):
        migration.upgrade()
        legacy_connection.execute(text("UPDATE vocabulary_study_memberships SET policy_level = 4 WHERE user_id = 1 AND word_id = 1"))
        with pytest.raises(RuntimeError, match="study data changed"):
            migration.downgrade()


def test_backfill_preserves_mastered_skipped_and_learning_policies(legacy_connection):
    connection = legacy_connection
    connection.execute(JapaneseDictionary.__table__.insert(), [
        {"word_id": 3, "source_entry_id": 3, "senses": []},
        {"word_id": 4, "source_entry_id": 4, "senses": []},
    ])
    connection.execute(JapaneseWordFamiliarity.__table__.insert(), [
        {"user_id": 1, "word_id": 3, "familiarity_score": -1},
        {"user_id": 1, "word_id": 4, "familiarity_score": 3},
    ])
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    scheduler = Scheduler(enable_fuzzing=False)
    for card_id, word_id in ((3, 2), (4, 3), (5, 4)):
        card = Card(card_id=card_id, due=now)
        if word_id in (2, 3):
            card, _ = scheduler.review_card(card, Rating.Good, review_datetime=now)
            card, _ = scheduler.review_card(card, Rating.Good, review_datetime=now + timedelta(minutes=10))
        connection.execute(StudyCard.__table__.insert(), {
            "id": card_id, "user_id": 1, "word_id": word_id, "occurrence_key": str(card_id),
            "sentence": "例文。", "target_text": "例", "reading": "れい", "definitions": [],
            "sentence_start": 0, "sentence_end": 3, "target_start": 0, "target_end": 1,
            "created_at": now, "due_at": card.due, "fsrs_card": card.to_dict(),
            "scheduler_version": "py-fsrs-6.3.3/fsrs-6", "scheduler_config": scheduler.to_dict(), "version": 0,
        })
    with Operations.context(MigrationContext.configure(connection)):
        _migration().upgrade()
        rows = connection.execute(text("SELECT word_id, review_status, next_eligible_at FROM vocabulary_study_schedules ORDER BY word_id")).all()
        assert [(row.word_id, row.review_status) for row in rows] == [(1, "deferred"), (2, "mastered"), (3, "wont_learn"), (4, "normal")]
        assert rows[1].next_eligible_at is None and rows[2].next_eligible_at is None
        assert rows[3].next_eligible_at is not None


def test_sentence_migration_preserves_independent_and_shared_history(legacy_connection):
    connection = legacy_connection
    with Operations.context(MigrationContext.configure(connection)):
        _migration().upgrade()
        metadata = MetaData()
        schedules = Table("vocabulary_study_schedules", metadata, autoload_with=connection)
        reviews = Table("vocabulary_study_review_logs", metadata, autoload_with=connection)
        shared = connection.execute(select(schedules)).mappings().one()
        assert shared["legacy_card_id"] == 2
        previous = Card.from_dict(shared["serialized_state"])
        scheduler = Scheduler.from_dict(shared["scheduler_config"])
        when = datetime(2025, 2, 1, tzinfo=timezone.utc)
        current, log = scheduler.review_card(previous, Rating.Good, review_datetime=when)
        connection.execute(schedules.update().values(serialized_state=current.to_dict(), next_review_at=current.due, version=2))
        connection.execute(reviews.insert().values(user_id=1, word_id=1, rating=3, reviewed_at=when,
            review_log=log.to_dict(), model_version=shared["model_version"], before_state=previous.to_dict(),
            after_state=current.to_dict(), legacy_review_id=None))
        sentence = _sentence_migration()
        sentence.upgrade()
        assert connection.execute(text("SELECT count(*) FROM sentence_study_memberships")).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM sentence_study_occurrences")).scalar_one() == 2
        rows = connection.execute(text("SELECT card_id, version FROM sentence_study_schedules ORDER BY card_id")).all()
        assert rows == [(1, 1), (2, 2)]
        logs = connection.execute(text("SELECT card_id, provenance, legacy_review_id FROM sentence_study_review_logs ORDER BY id")).all()
        assert logs == [(1, "card", 1), (2, "card", 2), (2, "legacy_shared", None)]
        assert connection.execute(text("SELECT count(*) FROM study_reviews")).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM vocabulary_study_review_logs")).scalar_one() == 3
        sentence.downgrade()
        assert connection.execute(text("SELECT count(*) FROM vocabulary_study_review_logs")).scalar_one() == 3


def test_sentence_migration_falls_back_to_serialized_source_and_guards_downgrade(legacy_connection):
    connection = legacy_connection
    with Operations.context(MigrationContext.configure(connection)):
        _migration().upgrade()
        connection.execute(text("UPDATE vocabulary_study_schedules SET legacy_card_id = NULL"))
        sentence = _sentence_migration()
        sentence.upgrade()
        assert connection.execute(text("SELECT count(*) FROM sentence_study_schedules")).scalar_one() == 2
        connection.execute(text("UPDATE sentence_study_memberships SET active = false, removed_at = CURRENT_TIMESTAMP WHERE card_id = 1"))
        with pytest.raises(RuntimeError, match="sentence study data changed"):
            sentence.downgrade()


def test_sentence_migration_preserves_deactivated_word_membership(legacy_connection):
    connection = legacy_connection
    with Operations.context(MigrationContext.configure(connection)):
        _migration().upgrade()
        connection.execute(text("UPDATE vocabulary_study_memberships SET active = false, removed_at = CURRENT_TIMESTAMP"))
        _sentence_migration().upgrade()
        rows = connection.execute(text("SELECT active, removed_at FROM sentence_study_memberships ORDER BY card_id")).all()
        assert len(rows) == 2
        assert all(not row.active and row.removed_at is not None for row in rows)
