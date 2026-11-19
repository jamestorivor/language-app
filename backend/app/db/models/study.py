from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class StudyCard(Base):
    __tablename__ = "study_cards"
    __table_args__ = (
        UniqueConstraint("user_id", "occurrence_key", name="uq_study_card_occurrence"),
        Index("ix_study_cards_user_due", "user_id", "due_at"),
        Index("uq_study_card_id_user_word", "id", "user_id", "word_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    word_id: Mapped[int] = mapped_column(ForeignKey("japanese_dictionary.word_id"), nullable=False)
    # This key remains stable when the source segment is deleted.
    occurrence_key: Mapped[str] = mapped_column(String(64), nullable=False)
    episode_id: Mapped[int | None] = mapped_column(ForeignKey("podcasts.id", ondelete="SET NULL"), nullable=True)
    segment_id: Mapped[int | None] = mapped_column(ForeignKey("podcast_chunk.id", ondelete="SET NULL"), nullable=True)
    episode_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentence: Mapped[str] = mapped_column(Text, nullable=False)
    target_text: Mapped[str] = mapped_column(Text, nullable=False)
    dictionary_form: Mapped[str | None] = mapped_column(Text)
    reading: Mapped[str] = mapped_column(Text, nullable=False)
    definitions: Mapped[list] = mapped_column(JSON, nullable=False)
    sentence_start: Mapped[int] = mapped_column(Integer, nullable=False)
    sentence_end: Mapped[int] = mapped_column(Integer, nullable=False)
    target_start: Mapped[int] = mapped_column(Integer, nullable=False)
    target_end: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Full py-fsrs serialized Card, including stability, difficulty and steps.
    fsrs_card: Mapped[dict] = mapped_column(JSON, nullable=False)
    scheduler_version: Mapped[str] = mapped_column(String(40), nullable=False)
    scheduler_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class StudyReview(Base):
    __tablename__ = "study_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("study_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    before_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    after_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    review_log: Mapped[dict] = mapped_column(JSON, nullable=False)
    scheduler_version: Mapped[str] = mapped_column(String(40), nullable=False)


class StudyMembership(Base):
    """One durable enrollment record per selected sentence card."""
    __tablename__ = "sentence_study_memberships"
    __table_args__ = (
        ForeignKeyConstraint(["card_id", "user_id", "word_id"], ["study_cards.id", "study_cards.user_id", "study_cards.word_id"]),
        UniqueConstraint("card_id", "user_id", "word_id", name="uq_sentence_membership_card_owner_word"),
        CheckConstraint("(active AND removed_at IS NULL) OR (NOT active AND removed_at IS NOT NULL)", name="ck_sentence_membership_status"),
        Index("ix_sentence_memberships_user_active", "user_id", "active"),
    )

    card_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    word_id: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WordStudyFamiliarity(Base):
    """Shared familiarity policy metadata for all sentence cards of a word."""
    __tablename__ = "sentence_study_familiarity"
    __table_args__ = (
        CheckConstraint("(policy_level IS NULL AND level_source IS NULL) OR (policy_level IS NOT NULL AND level_source IS NOT NULL AND policy_level BETWEEN 1 AND 5 AND level_source IN ('auto', 'manual'))", name="ck_sentence_familiarity_policy_level"),
        CheckConstraint("manual_level IS NULL OR manual_level BETWEEN 1 AND 5", name="ck_sentence_familiarity_manual_level"),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("japanese_dictionary.word_id"), primary_key=True)
    policy_level: Mapped[int | None] = mapped_column(Integer)
    manual_level: Mapped[int | None] = mapped_column(Integer)
    level_source: Mapped[str | None] = mapped_column(String(8))


class WordStudySchedule(Base):
    __tablename__ = "sentence_study_schedules"
    __table_args__ = (
        ForeignKeyConstraint(["card_id", "user_id", "word_id"], ["sentence_study_memberships.card_id", "sentence_study_memberships.user_id", "sentence_study_memberships.word_id"]),
        CheckConstraint("review_status IN ('normal', 'deferred', 'mastered', 'wont_learn')", name="ck_sentence_schedule_review_status"),
        CheckConstraint("version >= 0", name="ck_sentence_schedule_version"),
        Index("ix_sentence_schedule_user_due", "user_id", "next_eligible_at", postgresql_where=text("review_status IN ('normal', 'deferred')"), sqlite_where=text("review_status IN ('normal', 'deferred')")),
    )

    card_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    word_id: Mapped[int] = mapped_column(Integer, nullable=False)
    serialized_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    scheduler_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    legacy_card_id: Mapped[int | None] = mapped_column(Integer)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_status: Mapped[str] = mapped_column(String(12), nullable=False)
    next_eligible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class VocabularyOccurrence(Base):
    __tablename__ = "sentence_study_occurrences"
    __table_args__ = (
        ForeignKeyConstraint(["card_id", "user_id", "word_id"], ["study_cards.id", "study_cards.user_id", "study_cards.word_id"]),
        ForeignKeyConstraint(["episode_id", "episode_owner_id"], ["podcasts.id", "podcasts.user_id"], ondelete="SET NULL"),
        ForeignKeyConstraint(["segment_id", "segment_episode_id", "segment_owner_id"], ["podcast_chunk.id", "podcast_chunk.podcast_id", "podcast_chunk.user_id"], ondelete="SET NULL"),
        CheckConstraint("(episode_id IS NULL AND episode_owner_id IS NULL) OR (episode_id IS NOT NULL AND episode_owner_id IS NOT NULL AND episode_owner_id = user_id)", name="ck_sentence_occurrence_episode_owner"),
        CheckConstraint("(segment_id IS NULL AND segment_episode_id IS NULL AND segment_owner_id IS NULL) OR (segment_id IS NOT NULL AND segment_episode_id IS NOT NULL AND segment_owner_id IS NOT NULL AND segment_owner_id = user_id)", name="ck_sentence_occurrence_segment_owner"),
        CheckConstraint("episode_id IS NULL OR segment_episode_id IS NULL OR episode_id = segment_episode_id", name="ck_sentence_occurrence_segment_episode"),
        CheckConstraint("(start_ms IS NULL OR start_ms >= 0) AND (end_ms IS NULL OR (start_ms IS NOT NULL AND end_ms >= start_ms))", name="ck_sentence_occurrence_times"),
        Index("ix_sentence_occurrences_user_word", "user_id", "word_id"),
        Index("ix_sentence_occurrences_episode", "episode_id"),
        Index("ix_sentence_occurrences_segment", "segment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    word_id: Mapped[int] = mapped_column(ForeignKey("japanese_dictionary.word_id"), nullable=False)
    episode_id: Mapped[int | None] = mapped_column(Integer)
    episode_owner_id: Mapped[int | None] = mapped_column(Integer)
    segment_id: Mapped[int | None] = mapped_column(Integer)
    segment_episode_id: Mapped[int | None] = mapped_column(Integer)
    segment_owner_id: Mapped[int | None] = mapped_column(Integer)
    sentence: Mapped[str] = mapped_column(Text, nullable=False)
    surface_form: Mapped[str] = mapped_column(Text, nullable=False)
    start_ms: Mapped[int | None] = mapped_column(Integer)
    end_ms: Mapped[int | None] = mapped_column(Integer)
    episode_title: Mapped[str | None] = mapped_column(Text)
    legacy_card_id: Mapped[int | None] = mapped_column(Integer, unique=True)


class WordStudyReview(Base):
    __tablename__ = "sentence_study_review_logs"
    __table_args__ = (
        ForeignKeyConstraint(["card_id", "user_id", "word_id"], ["sentence_study_memberships.card_id", "sentence_study_memberships.user_id", "sentence_study_memberships.word_id"]),
        CheckConstraint("rating BETWEEN 1 AND 4", name="ck_sentence_review_rating"),
        CheckConstraint("provenance IN ('card', 'legacy_shared')", name="ck_sentence_review_provenance"),
        Index("ix_sentence_reviews_user_word_time", "user_id", "word_id", "reviewed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(nullable=False)
    word_id: Mapped[int] = mapped_column(nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_log: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSON)
    after_state: Mapped[dict | None] = mapped_column(JSON)
    legacy_review_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    legacy_shared_review_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    provenance: Mapped[str] = mapped_column(String(20), nullable=False, default="card", server_default=text("'card'"))


class LegacySentenceCardArchive(Base):
    """Original independent schedules retained after word-level consolidation."""
    __tablename__ = "legacy_sentence_card_archive"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    word_id: Mapped[int] = mapped_column(Integer, nullable=False)
    occurrence_key: Mapped[str] = mapped_column(String(64), nullable=False)
    episode_id: Mapped[int | None] = mapped_column(Integer)
    segment_id: Mapped[int | None] = mapped_column(Integer)
    episode_title: Mapped[str | None] = mapped_column(Text)
    sentence: Mapped[str] = mapped_column(Text, nullable=False)
    target_text: Mapped[str] = mapped_column(Text, nullable=False)
    reading: Mapped[str] = mapped_column(Text, nullable=False)
    definitions: Mapped[list] = mapped_column(JSON, nullable=False)
    sentence_start: Mapped[int] = mapped_column(Integer, nullable=False)
    sentence_end: Mapped[int] = mapped_column(Integer, nullable=False)
    target_start: Mapped[int] = mapped_column(Integer, nullable=False)
    target_end: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fsrs_card: Mapped[dict] = mapped_column(JSON, nullable=False)
    scheduler_version: Mapped[str] = mapped_column(String(40), nullable=False)
    scheduler_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)


class WordStudyMigrationGuard(Base):
    """Fingerprint for rejecting downgrades that would discard new data."""
    __tablename__ = "word_study_migration_guard"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class SentenceStudyMigrationGuard(Base):
    __tablename__ = "sentence_study_migration_guard"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
