"""Add separate word study structures without modifying legacy sentence cards.

Revision ID: e7a4c6b09f11
Revises: d2e6f8a9b001

Only previously explicitly selected sentence cards are migrated. Their original
independent schedules are archived; the most recently reviewed schedule wins.
"""
from alembic import op
import sqlalchemy as sa

revision = "e7a4c6b09f11"
down_revision = "d2e6f8a9b001"
branch_labels = None
depends_on = None


def _snapshot_hash(connection):
    """Detect changes that cannot be represented by the legacy schema."""
    import hashlib
    import json

    tables = (
        ("study_cards", "id"), ("study_reviews", "id"),
        ("legacy_sentence_card_archive", "id"),
        ("vocabulary_study_memberships", "user_id, word_id"),
        ("vocabulary_study_schedules", "user_id, word_id"),
        ("vocabulary_occurrences", "id"), ("vocabulary_study_review_logs", "id"),
    )
    digest = hashlib.sha256()
    for table, order in tables:
        digest.update(table.encode())
        for row in connection.execute(sa.text(f"SELECT * FROM {table} ORDER BY {order}")).mappings():
            digest.update(json.dumps(dict(row), sort_keys=True, ensure_ascii=False, default=str).encode())
            digest.update(b"\n")
    return digest.hexdigest()


def _backfill_eligibility(card, scheduler, level):
    """Frozen initial policy; a historical migration must not import live policy."""
    from datetime import datetime, timedelta, timezone
    from fsrs import State

    if level == -1:
        return "wont_learn", None
    if level == 5:
        return "mastered", None
    if level not in (3, 4) or card.state != State.Review or card.last_review is None or card.stability is None:
        return "normal", card.due
    last_review = card.last_review.astimezone(timezone.utc)
    max_days = (datetime.max.replace(tzinfo=timezone.utc) - last_review).days

    def reaches(day):
        return scheduler.get_card_retrievability(card, last_review + timedelta(days=day)) <= 0.8

    if reaches(0):
        return "deferred", last_review
    if max_days == 0:
        raise OverflowError("forgetting threshold exceeds representable datetime")
    lower, upper = 0, 1
    while upper < max_days and not reaches(upper):
        lower, upper = upper, min(upper * 2, max_days)
    if not reaches(upper):
        raise OverflowError("forgetting threshold exceeds representable datetime")
    while lower + 1 < upper:
        middle = (lower + upper) // 2
        if reaches(middle):
            upper = middle
        else:
            lower = middle
    return "deferred", last_review + timedelta(days=upper)


def upgrade():
    if op.get_context().as_sql:
        raise RuntimeError("This migration requires an online database to migrate existing FSRS schedules")
    op.create_index("uq_podcasts_id_user", "podcasts", ["id", "user_id"], unique=True)
    op.create_index("uq_podcast_chunk_id_episode_user", "podcast_chunk", ["id", "podcast_id", "user_id"], unique=True)
    op.create_table(
        "vocabulary_study_memberships",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("word_id", sa.Integer, sa.ForeignKey("japanese_dictionary.word_id"), primary_key=True),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        sa.Column("policy_level", sa.Integer),
        sa.Column("manual_level", sa.Integer),
        sa.Column("level_source", sa.String(8)),
        sa.CheckConstraint("(active AND removed_at IS NULL) OR (NOT active AND removed_at IS NOT NULL)", name="ck_study_membership_status"),
        sa.CheckConstraint("(policy_level IS NULL AND level_source IS NULL) OR (policy_level IS NOT NULL AND level_source IS NOT NULL AND policy_level BETWEEN 1 AND 5 AND level_source IN ('auto', 'manual'))", name="ck_study_membership_policy_level"),
        sa.CheckConstraint("manual_level IS NULL OR manual_level BETWEEN 1 AND 5", name="ck_study_membership_manual_level"),
    )
    op.create_index("ix_study_memberships_user_active", "vocabulary_study_memberships", ["user_id", "active"])
    op.create_table(
        "vocabulary_study_schedules",
        sa.Column("user_id", sa.Integer, primary_key=True),
        sa.Column("word_id", sa.Integer, primary_key=True),
        sa.Column("serialized_state", sa.JSON, nullable=False),
        sa.Column("scheduler_config", sa.JSON, nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("legacy_card_id", sa.Integer),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_status", sa.String(12), nullable=False),
        sa.Column("next_eligible_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(["user_id", "word_id"], ["vocabulary_study_memberships.user_id", "vocabulary_study_memberships.word_id"]),
        sa.CheckConstraint("review_status IN ('normal', 'deferred', 'mastered', 'wont_learn')", name="ck_word_schedule_review_status"),
        sa.CheckConstraint("version >= 0", name="ck_word_schedule_version"),
    )
    op.create_index("ix_word_schedule_user_due", "vocabulary_study_schedules", ["user_id", "next_eligible_at"],
                    postgresql_where=sa.text("review_status IN ('normal', 'deferred')"), sqlite_where=sa.text("review_status IN ('normal', 'deferred')"))
    op.create_table(
        "vocabulary_occurrences",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("word_id", sa.Integer, sa.ForeignKey("japanese_dictionary.word_id"), nullable=False),
        sa.Column("episode_id", sa.Integer),
        sa.Column("episode_owner_id", sa.Integer),
        sa.Column("segment_id", sa.Integer),
        sa.Column("segment_episode_id", sa.Integer),
        sa.Column("segment_owner_id", sa.Integer),
        sa.Column("sentence", sa.Text, nullable=False),
        sa.Column("surface_form", sa.Text, nullable=False),
        sa.Column("start_ms", sa.Integer),
        sa.Column("end_ms", sa.Integer),
        sa.Column("episode_title", sa.Text),
        sa.Column("legacy_card_id", sa.Integer, unique=True),
        sa.ForeignKeyConstraint(["episode_id", "episode_owner_id"], ["podcasts.id", "podcasts.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["segment_id", "segment_episode_id", "segment_owner_id"], ["podcast_chunk.id", "podcast_chunk.podcast_id", "podcast_chunk.user_id"], ondelete="SET NULL"),
        sa.CheckConstraint("(episode_id IS NULL AND episode_owner_id IS NULL) OR (episode_id IS NOT NULL AND episode_owner_id IS NOT NULL AND episode_owner_id = user_id)", name="ck_occurrence_episode_owner"),
        sa.CheckConstraint("(segment_id IS NULL AND segment_episode_id IS NULL AND segment_owner_id IS NULL) OR (segment_id IS NOT NULL AND segment_episode_id IS NOT NULL AND segment_owner_id IS NOT NULL AND segment_owner_id = user_id)", name="ck_occurrence_segment_owner"),
        sa.CheckConstraint("episode_id IS NULL OR segment_episode_id IS NULL OR episode_id = segment_episode_id", name="ck_occurrence_segment_episode"),
        sa.CheckConstraint("(start_ms IS NULL OR start_ms >= 0) AND (end_ms IS NULL OR (start_ms IS NOT NULL AND end_ms >= start_ms))", name="ck_occurrence_times"),
    )
    op.create_index("ix_vocabulary_occurrences_user_word", "vocabulary_occurrences", ["user_id", "word_id"])
    op.create_index("ix_vocabulary_occurrences_episode", "vocabulary_occurrences", ["episode_id"])
    op.create_index("ix_vocabulary_occurrences_segment", "vocabulary_occurrences", ["segment_id"])
    op.create_table(
        "vocabulary_study_review_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("word_id", sa.Integer, nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_log", sa.JSON, nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("before_state", sa.JSON),
        sa.Column("after_state", sa.JSON),
        sa.Column("legacy_review_id", sa.Integer, unique=True),
        sa.ForeignKeyConstraint(["user_id", "word_id"], ["vocabulary_study_memberships.user_id", "vocabulary_study_memberships.word_id"]),
        sa.CheckConstraint("rating BETWEEN 1 AND 4", name="ck_word_review_rating"),
    )
    op.create_index("ix_word_reviews_user_word_time", "vocabulary_study_review_logs", ["user_id", "word_id", "reviewed_at"])
    op.create_table(
        "legacy_sentence_card_archive",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("user_id", sa.Integer, nullable=False), sa.Column("word_id", sa.Integer, nullable=False),
        sa.Column("occurrence_key", sa.String(64), nullable=False),
        sa.Column("episode_id", sa.Integer), sa.Column("segment_id", sa.Integer), sa.Column("episode_title", sa.Text),
        sa.Column("sentence", sa.Text, nullable=False), sa.Column("target_text", sa.Text, nullable=False),
        sa.Column("reading", sa.Text, nullable=False), sa.Column("definitions", sa.JSON, nullable=False),
        sa.Column("sentence_start", sa.Integer, nullable=False), sa.Column("sentence_end", sa.Integer, nullable=False),
        sa.Column("target_start", sa.Integer, nullable=False), sa.Column("target_end", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fsrs_card", sa.JSON, nullable=False), sa.Column("scheduler_version", sa.String(40), nullable=False),
        sa.Column("scheduler_config", sa.JSON, nullable=False), sa.Column("version", sa.Integer, nullable=False),
    )

    # Keep every original state even when several sentence cards share a word.
    op.execute("INSERT INTO legacy_sentence_card_archive SELECT * FROM study_cards")
    op.execute("""
        INSERT INTO vocabulary_study_memberships
          (user_id, word_id, active, added_at, removed_at, policy_level, manual_level, level_source)
        SELECT cards.user_id, cards.word_id, true, MIN(cards.created_at), NULL,
          CASE WHEN MAX(progress.familiarity_score) BETWEEN 1 AND 5 THEN MAX(progress.familiarity_score) ELSE NULL END,
          CASE WHEN MAX(progress.familiarity_score) BETWEEN 1 AND 5 THEN MAX(progress.familiarity_score) ELSE NULL END,
          CASE WHEN MAX(progress.familiarity_score) BETWEEN 1 AND 5 THEN 'manual' ELSE NULL END
        FROM study_cards cards LEFT JOIN user_japanese_word_progress progress
          ON progress.user_id = cards.user_id AND progress.word_id = cards.word_id
        GROUP BY cards.user_id, cards.word_id
    """)
    op.execute("""
        INSERT INTO vocabulary_study_schedules
          (user_id, word_id, serialized_state, scheduler_config, model_version, legacy_card_id,
           next_review_at, review_status, next_eligible_at, version)
        SELECT user_id, word_id, fsrs_card, scheduler_config, scheduler_version, id,
               due_at, 'normal', due_at, version
        FROM (
          SELECT cards.*, ROW_NUMBER() OVER (
            PARTITION BY cards.user_id, cards.word_id
            ORDER BY CASE WHEN last_review.last_reviewed IS NULL THEN 1 ELSE 0 END,
                     last_review.last_reviewed DESC, cards.created_at DESC, cards.id DESC
          ) AS rank_number
          FROM study_cards cards LEFT JOIN (
            SELECT card_id, MAX(reviewed_at) AS last_reviewed FROM study_reviews GROUP BY card_id
          ) last_review ON last_review.card_id = cards.id
        ) ranked WHERE rank_number = 1
    """)
    op.execute("""
        INSERT INTO vocabulary_occurrences
          (user_id, word_id, episode_id, episode_owner_id, segment_id, segment_episode_id,
           segment_owner_id, sentence, surface_form, start_ms, end_ms, episode_title, legacy_card_id)
        SELECT c.user_id, c.word_id, e.id, e.user_id, s.id, s.podcast_id, s.user_id,
               c.sentence, c.target_text, NULL, NULL, c.episode_title, c.id
        FROM study_cards c
        LEFT JOIN podcasts e ON e.id = c.episode_id AND e.user_id = c.user_id
        LEFT JOIN podcast_chunk s ON s.id = c.segment_id AND s.user_id = c.user_id
          AND (e.id IS NULL OR s.podcast_id = e.id)
    """)
    op.execute("""
        INSERT INTO vocabulary_study_review_logs
          (user_id, word_id, rating, reviewed_at, review_log, model_version, before_state, after_state, legacy_review_id)
        SELECT c.user_id, c.word_id, r.rating, r.reviewed_at, r.review_log,
               r.scheduler_version, r.before_state, r.after_state, r.id
        FROM study_reviews r JOIN study_cards c ON c.id = r.card_id
    """)

    # Recompute application eligibility while preserving each selected FSRS state.
    import json
    from fsrs import Card, Scheduler

    connection = op.get_bind()
    rows = connection.execute(sa.text("""
        SELECT s.user_id, s.word_id, s.serialized_state, s.scheduler_config,
               p.familiarity_score
        FROM vocabulary_study_schedules s LEFT JOIN user_japanese_word_progress p
          ON p.user_id = s.user_id AND p.word_id = s.word_id
    """)).mappings().all()
    for row in rows:
        state = json.loads(row["serialized_state"]) if isinstance(row["serialized_state"], str) else row["serialized_state"]
        config = json.loads(row["scheduler_config"]) if isinstance(row["scheduler_config"], str) else row["scheduler_config"]
        status, eligible = _backfill_eligibility(Card.from_dict(state), Scheduler.from_dict(config), row["familiarity_score"])
        connection.execute(sa.text("""
            UPDATE vocabulary_study_schedules SET review_status = :status, next_eligible_at = :eligible
            WHERE user_id = :user_id AND word_id = :word_id
        """), {"status": status, "eligible": eligible,
                "user_id": row["user_id"], "word_id": row["word_id"]})
    op.create_table("word_study_migration_guard",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("snapshot_hash", sa.String(64), nullable=False))
    connection.execute(sa.text("INSERT INTO word_study_migration_guard (id, snapshot_hash) VALUES (1, :snapshot)"),
                       {"snapshot": _snapshot_hash(connection)})


def downgrade():
    # Reject a destructive downgrade instead of discarding newly-created data.
    if op.get_context().as_sql:
        raise RuntimeError("Offline downgrade is unsupported: check that word study tables are empty first")
    connection = op.get_bind()
    saved = connection.execute(sa.text("SELECT snapshot_hash FROM word_study_migration_guard WHERE id = 1")).scalar_one()
    if saved != _snapshot_hash(connection):
        raise RuntimeError("Cannot downgrade: study data changed since migration and would be lost")
    op.drop_table("word_study_migration_guard")
    op.drop_table("vocabulary_study_review_logs")
    op.drop_table("vocabulary_occurrences")
    op.drop_table("vocabulary_study_schedules")
    op.drop_table("vocabulary_study_memberships")
    op.drop_table("legacy_sentence_card_archive")
    op.drop_index("uq_podcast_chunk_id_episode_user", table_name="podcast_chunk")
    op.drop_index("uq_podcasts_id_user", table_name="podcasts")
