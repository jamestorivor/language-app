from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
# Register the referenced table when podcast models are imported on their own.
from app.db.models import user as _user  # noqa: F401


class PodcastEpisode(Base):
    __tablename__ = "podcasts"
    __table_args__ = (
        UniqueConstraint("user_id", "audio_location", name="uq_podcasts_user_audio"),
        CheckConstraint("language IN ('ja', 'en')", name="valid_podcast_language"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id : Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    audio_location: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str]
    author: Mapped[str]
    duration: Mapped[float]
    language: Mapped[str] = mapped_column(String(2), nullable=False, default="ja", server_default=text("'ja'"))
    added_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        default=lambda: datetime.now(timezone.utc), server_default=func.now(),
    )

class PodcastChunk(Base):
    __tablename__ = "podcast_chunk"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    podcast_id: Mapped[int] = mapped_column(ForeignKey("podcasts.id"), index=True)
    start_time: Mapped[float]
    end_time: Mapped[float]

    episode: Mapped["PodcastEpisode"] = relationship()

    @property
    def episode_title(self) -> str:
        return self.episode.title

    @property
    def episode_author(self) -> str:
        return self.episode.author

    @property
    def episode_language(self) -> str:
        return self.episode.language

    transcript: Mapped["PodcastTranscript | None"] = relationship(
        back_populates="podcast_chunk", cascade="all, delete-orphan", uselist=False
    )


class PodcastTranscript(Base):
    __tablename__ = "podcast_transcript"

    id: Mapped[int] = mapped_column(primary_key=True)
    podcast_chunk_id: Mapped[int] = mapped_column(ForeignKey("podcast_chunk.id"), unique=True)
    text: Mapped[str]

    podcast_chunk: Mapped["PodcastChunk"] = relationship(back_populates="transcript")


class PodcastVocabularyBaseline(Base):
    __tablename__ = "podcast_vocabulary_baseline"

    episode_id: Mapped[int] = mapped_column(ForeignKey("podcasts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    language: Mapped[str] = mapped_column(String(2))
    scores: Mapped[dict] = mapped_column(JSON)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PodcastVocabularyAnalysis(Base):
    __tablename__ = "podcast_vocabulary_analysis"

    chunk_id: Mapped[int] = mapped_column(ForeignKey("podcast_chunk.id", ondelete="CASCADE"), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    counts: Mapped[dict] = mapped_column(JSON)
    unmatched: Mapped[int]
