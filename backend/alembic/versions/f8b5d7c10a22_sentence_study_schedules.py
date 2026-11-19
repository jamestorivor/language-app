"""Restore separate schedules for each selected sentence card.

Revision ID: f8b5d7c10a22
Revises: e7a4c6b09f11

The earlier word-level tables and original card archive remain intact. Reviews
performed while schedules were shared retain explicit uncertain provenance.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone

from alembic import op
from fsrs import Card, Scheduler, State
import sqlalchemy as sa

revision = "f8b5d7c10a22"
down_revision = "e7a4c6b09f11"
branch_labels = None
depends_on = None


def _value(value):
    return json.loads(value) if isinstance(value, str) else value


def _eligibility(card, scheduler, level):
    # Frozen initial policy: only reviewed level 3/4 cards wait until 80%.
    if level == -1:
        return "wont_learn", None
    if level == 5:
        return "mastered", None
    if level not in (3, 4) or card.state != State.Review or card.last_review is None or card.stability is None:
        return "normal", card.due
    last = card.last_review.astimezone(timezone.utc)
    maximum = (datetime.max.replace(tzinfo=timezone.utc) - last).days
    def reaches(day):
        return scheduler.get_card_retrievability(card, last + timedelta(days=day)) <= 0.8
    if reaches(0):
        return "deferred", last
    if maximum == 0:
        raise OverflowError("forgetting threshold exceeds representable datetime")
    low, high = 0, 1
    while high < maximum and not reaches(high):
        low, high = high, min(high * 2, maximum)
    if not reaches(high):
        raise OverflowError("forgetting threshold exceeds representable datetime")
    while low + 1 < high:
        middle = (low + high) // 2
        if reaches(middle):
            high = middle
        else:
            low = middle
    return "deferred", last + timedelta(days=high)


def _snapshot_hash(connection):
    tables = (
        ("study_cards", "id"), ("study_reviews", "id"), ("legacy_sentence_card_archive", "id"),
        ("vocabulary_study_memberships", "user_id, word_id"),
        ("vocabulary_study_schedules", "user_id, word_id"), ("vocabulary_occurrences", "id"),
        ("vocabulary_study_review_logs", "id"),
        ("sentence_study_memberships", "card_id"), ("sentence_study_schedules", "card_id"),
        ("sentence_study_familiarity", "user_id, word_id"),
        ("sentence_study_occurrences", "id"), ("sentence_study_review_logs", "id"),
    )
    digest = hashlib.sha256()
    for table, ordering in tables:
        digest.update(table.encode())
        for row in connection.execute(sa.text(f"SELECT * FROM {table} ORDER BY {ordering}")).mappings():
            digest.update(json.dumps(dict(row), sort_keys=True, ensure_ascii=False, default=str).encode())
            digest.update(b"\n")
    return digest.hexdigest()


def upgrade():
    if op.get_context().as_sql:
        raise RuntimeError("Sentence study migration requires an online database")
    connection = op.get_bind()
    op.create_index("uq_study_card_id_user_word", "study_cards", ["id", "user_id", "word_id"], unique=True)
    op.create_table("sentence_study_memberships",
        sa.Column("card_id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("user_id", sa.Integer, nullable=False), sa.Column("word_id", sa.Integer, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False), sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["card_id", "user_id", "word_id"], ["study_cards.id", "study_cards.user_id", "study_cards.word_id"]),
        sa.UniqueConstraint("card_id", "user_id", "word_id", name="uq_sentence_membership_card_owner_word"),
        sa.CheckConstraint("(active AND removed_at IS NULL) OR (NOT active AND removed_at IS NOT NULL)", name="ck_sentence_membership_status"))
    op.create_index("ix_sentence_memberships_user_active", "sentence_study_memberships", ["user_id", "active"])
    op.create_table("sentence_study_familiarity",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("word_id", sa.Integer, sa.ForeignKey("japanese_dictionary.word_id"), primary_key=True),
        sa.Column("policy_level", sa.Integer), sa.Column("manual_level", sa.Integer), sa.Column("level_source", sa.String(8)),
        sa.CheckConstraint("(policy_level IS NULL AND level_source IS NULL) OR (policy_level IS NOT NULL AND level_source IS NOT NULL AND policy_level BETWEEN 1 AND 5 AND level_source IN ('auto', 'manual'))", name="ck_sentence_familiarity_policy_level"),
        sa.CheckConstraint("manual_level IS NULL OR manual_level BETWEEN 1 AND 5", name="ck_sentence_familiarity_manual_level"))
    schedule = op.create_table("sentence_study_schedules",
        sa.Column("card_id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("user_id", sa.Integer, nullable=False), sa.Column("word_id", sa.Integer, nullable=False),
        sa.Column("serialized_state", sa.JSON, nullable=False), sa.Column("scheduler_config", sa.JSON, nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False), sa.Column("legacy_card_id", sa.Integer),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=False), sa.Column("review_status", sa.String(12), nullable=False),
        sa.Column("next_eligible_at", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(["card_id", "user_id", "word_id"], ["sentence_study_memberships.card_id", "sentence_study_memberships.user_id", "sentence_study_memberships.word_id"]),
        sa.CheckConstraint("review_status IN ('normal', 'deferred', 'mastered', 'wont_learn')", name="ck_sentence_schedule_review_status"),
        sa.CheckConstraint("version >= 0", name="ck_sentence_schedule_version"))
    op.create_index("ix_sentence_schedule_user_due", "sentence_study_schedules", ["user_id", "next_eligible_at"],
        postgresql_where=sa.text("review_status IN ('normal', 'deferred')"), sqlite_where=sa.text("review_status IN ('normal', 'deferred')"))
    op.create_table("sentence_study_occurrences",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("card_id", sa.Integer, nullable=False, unique=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("word_id", sa.Integer, sa.ForeignKey("japanese_dictionary.word_id"), nullable=False),
        sa.Column("episode_id", sa.Integer), sa.Column("episode_owner_id", sa.Integer),
        sa.Column("segment_id", sa.Integer), sa.Column("segment_episode_id", sa.Integer), sa.Column("segment_owner_id", sa.Integer),
        sa.Column("sentence", sa.Text, nullable=False), sa.Column("surface_form", sa.Text, nullable=False),
        sa.Column("start_ms", sa.Integer), sa.Column("end_ms", sa.Integer), sa.Column("episode_title", sa.Text),
        sa.Column("legacy_card_id", sa.Integer, unique=True),
        sa.ForeignKeyConstraint(["card_id", "user_id", "word_id"], ["study_cards.id", "study_cards.user_id", "study_cards.word_id"]),
        sa.ForeignKeyConstraint(["episode_id", "episode_owner_id"], ["podcasts.id", "podcasts.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["segment_id", "segment_episode_id", "segment_owner_id"], ["podcast_chunk.id", "podcast_chunk.podcast_id", "podcast_chunk.user_id"], ondelete="SET NULL"),
        sa.CheckConstraint("(episode_id IS NULL AND episode_owner_id IS NULL) OR (episode_id IS NOT NULL AND episode_owner_id IS NOT NULL AND episode_owner_id = user_id)", name="ck_sentence_occurrence_episode_owner"),
        sa.CheckConstraint("(segment_id IS NULL AND segment_episode_id IS NULL AND segment_owner_id IS NULL) OR (segment_id IS NOT NULL AND segment_episode_id IS NOT NULL AND segment_owner_id IS NOT NULL AND segment_owner_id = user_id)", name="ck_sentence_occurrence_segment_owner"),
        sa.CheckConstraint("episode_id IS NULL OR segment_episode_id IS NULL OR episode_id = segment_episode_id", name="ck_sentence_occurrence_segment_episode"),
        sa.CheckConstraint("(start_ms IS NULL OR start_ms >= 0) AND (end_ms IS NULL OR (start_ms IS NOT NULL AND end_ms >= start_ms))", name="ck_sentence_occurrence_times"))
    op.create_index("ix_sentence_occurrences_user_word", "sentence_study_occurrences", ["user_id", "word_id"])
    op.create_index("ix_sentence_occurrences_episode", "sentence_study_occurrences", ["episode_id"])
    op.create_index("ix_sentence_occurrences_segment", "sentence_study_occurrences", ["segment_id"])
    reviews = op.create_table("sentence_study_review_logs",
        sa.Column("id", sa.Integer, primary_key=True), sa.Column("card_id", sa.Integer, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False), sa.Column("word_id", sa.Integer, nullable=False),
        sa.Column("rating", sa.Integer, nullable=False), sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_log", sa.JSON, nullable=False), sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("before_state", sa.JSON), sa.Column("after_state", sa.JSON),
        sa.Column("legacy_review_id", sa.Integer, unique=True), sa.Column("legacy_shared_review_id", sa.Integer, unique=True),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="card"),
        sa.ForeignKeyConstraint(["card_id", "user_id", "word_id"], ["sentence_study_memberships.card_id", "sentence_study_memberships.user_id", "sentence_study_memberships.word_id"]),
        sa.CheckConstraint("rating BETWEEN 1 AND 4", name="ck_sentence_review_rating"),
        sa.CheckConstraint("provenance IN ('card', 'legacy_shared')", name="ck_sentence_review_provenance"))
    op.create_index("ix_sentence_reviews_user_word_time", "sentence_study_review_logs", ["user_id", "word_id", "reviewed_at"])

    # Preserve existing explicit membership state; never enroll dictionary rows.
    op.execute("""INSERT INTO sentence_study_familiarity (user_id, word_id, policy_level, manual_level, level_source)
        SELECT user_id, word_id, policy_level, manual_level, level_source FROM vocabulary_study_memberships""")
    missing = connection.execute(sa.text("""SELECT c.id FROM study_cards c LEFT JOIN vocabulary_study_memberships m
        ON m.user_id = c.user_id AND m.word_id = c.word_id WHERE m.user_id IS NULL LIMIT 1""")).first()
    if missing:
        raise RuntimeError("A legacy sentence card has no word membership; migration cannot infer enrollment")
    op.execute("""INSERT INTO sentence_study_memberships (card_id, user_id, word_id, active, added_at, removed_at)
        SELECT c.id, c.user_id, c.word_id, m.active, c.created_at, m.removed_at
        FROM study_cards c JOIN vocabulary_study_memberships m ON m.user_id = c.user_id AND m.word_id = c.word_id""")
    op.execute("""INSERT INTO sentence_study_occurrences
       (card_id, user_id, word_id, episode_id, episode_owner_id, segment_id, segment_episode_id, segment_owner_id,
        sentence, surface_form, start_ms, end_ms, episode_title, legacy_card_id)
       SELECT c.id, c.user_id, c.word_id, COALESCE(o.episode_id, e.id), COALESCE(o.episode_owner_id, e.user_id),
        COALESCE(o.segment_id, s.id), COALESCE(o.segment_episode_id, s.podcast_id), COALESCE(o.segment_owner_id, s.user_id),
        COALESCE(o.sentence, c.sentence), COALESCE(o.surface_form, c.target_text), o.start_ms, o.end_ms,
        COALESCE(o.episode_title, c.episode_title), c.id
       FROM study_cards c LEFT JOIN vocabulary_occurrences o ON o.legacy_card_id = c.id
       LEFT JOIN podcasts e ON e.id = c.episode_id AND e.user_id = c.user_id
       LEFT JOIN podcast_chunk s ON s.id = c.segment_id AND s.user_id = c.user_id
          AND (e.id IS NULL OR s.podcast_id = e.id)""")

    shared = connection.execute(sa.text("SELECT * FROM vocabulary_study_schedules")).mappings().all()
    sources = {}
    for row in shared:
        state = _value(row["serialized_state"])
        source = row["legacy_card_id"] or state.get("card_id")
        valid = connection.execute(sa.text("SELECT 1 FROM study_cards WHERE id = :id AND user_id = :user AND word_id = :word"),
            {"id": source, "user": row["user_id"], "word": row["word_id"]}).first()
        if not valid:
            raise RuntimeError("Cannot identify the source of an existing shared schedule")
        sources[(row["user_id"], row["word_id"])] = (source, row)
    cards = connection.execute(sa.text("""SELECT c.*, a.fsrs_card AS archived_state, a.scheduler_config AS archived_config,
        a.scheduler_version AS archived_version, a.due_at AS archived_due, a.version AS archived_revision,
        p.familiarity_score FROM study_cards c LEFT JOIN legacy_sentence_card_archive a ON a.id = c.id
        LEFT JOIN user_japanese_word_progress p ON p.user_id = c.user_id AND p.word_id = c.word_id""")).mappings().all()
    for card in cards:
        source = sources.get((card["user_id"], card["word_id"]))
        if source is None:
            raise RuntimeError("A legacy membership has no corresponding schedule")
        if card["id"] == source[0]:
            selected = source[1]
            values = {key: selected[key] for key in ("serialized_state", "scheduler_config", "model_version", "next_review_at", "review_status", "next_eligible_at", "version")}
            values["serialized_state"] = _value(values["serialized_state"])
            values["scheduler_config"] = _value(values["scheduler_config"])
        else:
            state = _value(card["archived_state"] or card["fsrs_card"])
            config = _value(card["archived_config"] or card["scheduler_config"])
            status, eligible = _eligibility(Card.from_dict(state), Scheduler.from_dict(config), card["familiarity_score"])
            values = dict(serialized_state=state, scheduler_config=config,
                model_version=card["archived_version"] or card["scheduler_version"],
                next_review_at=card["archived_due"] or card["due_at"], review_status=status,
                next_eligible_at=eligible, version=card["archived_revision"] if card["archived_revision"] is not None else card["version"])
        # Typed JSON and datetime binds work on both supported dialects.
        for key in ("next_review_at", "next_eligible_at"):
            if isinstance(values[key], str):
                values[key] = datetime.fromisoformat(values[key])
        connection.execute(schedule.insert().values(card_id=card["id"], user_id=card["user_id"], word_id=card["word_id"],
                                                    legacy_card_id=card["id"], **values))
    old_reviews = connection.execute(sa.text("SELECT * FROM vocabulary_study_review_logs ORDER BY id")).mappings().all()
    for row in old_reviews:
        legacy_id = row["legacy_review_id"]
        if legacy_id is not None:
            original = connection.execute(sa.text("SELECT card_id FROM study_reviews WHERE id = :id"), {"id": legacy_id}).first()
            if original is None:
                raise RuntimeError("Cannot identify the original card for a migrated review")
            card_id, provenance = original.card_id, "card"
        else:
            entry = sources.get((row["user_id"], row["word_id"]))
            if entry is None:
                raise RuntimeError("Cannot identify the source of a shared review")
            card_id, provenance = entry[0], "legacy_shared"
        reviewed_at = row["reviewed_at"]
        if isinstance(reviewed_at, str):
            reviewed_at = datetime.fromisoformat(reviewed_at)
        connection.execute(reviews.insert().values(card_id=card_id, user_id=row["user_id"], word_id=row["word_id"],
            rating=row["rating"], reviewed_at=reviewed_at, review_log=_value(row["review_log"]), model_version=row["model_version"],
            before_state=_value(row["before_state"]) if row["before_state"] is not None else None,
            after_state=_value(row["after_state"]) if row["after_state"] is not None else None,
            legacy_review_id=legacy_id, legacy_shared_review_id=row["id"], provenance=provenance))
    op.create_table("sentence_study_migration_guard", sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("snapshot_hash", sa.String(64), nullable=False))
    connection.execute(sa.text("INSERT INTO sentence_study_migration_guard (id, snapshot_hash) VALUES (1, :snapshot)"),
                       {"snapshot": _snapshot_hash(connection)})


def downgrade():
    if op.get_context().as_sql:
        raise RuntimeError("Offline downgrade cannot verify preservation of sentence study data")
    connection = op.get_bind()
    saved = connection.execute(sa.text("SELECT snapshot_hash FROM sentence_study_migration_guard WHERE id = 1")).scalar_one()
    if saved != _snapshot_hash(connection):
        raise RuntimeError("Cannot downgrade: sentence study data changed since migration and would be lost")
    op.drop_table("sentence_study_migration_guard")
    op.drop_table("sentence_study_review_logs")
    op.drop_table("sentence_study_occurrences")
    op.drop_table("sentence_study_schedules")
    op.drop_table("sentence_study_familiarity")
    op.drop_table("sentence_study_memberships")
    op.drop_index("uq_study_card_id_user_word", table_name="study_cards")
