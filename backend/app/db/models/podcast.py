from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
# Register the referenced table when podcast models are imported on their own.
from app.db.models import user as _user  # noqa: F401


class PodcastEpisode(Base):
    __tablename__ = "podcasts"
    __table_args__ = (UniqueConstraint("user_id", "audio_location", name="uq_podcasts_user_audio"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id : Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    audio_location: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str]
    author: Mapped[str]
    duration: Mapped[float]

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

    transcript: Mapped["PodcastTranscript | None"] = relationship(
        back_populates="podcast_chunk", cascade="all, delete-orphan", uselist=False
    )


class PodcastTranscript(Base):
    __tablename__ = "podcast_transcript"

    id: Mapped[int] = mapped_column(primary_key=True)
    podcast_chunk_id: Mapped[int] = mapped_column(ForeignKey("podcast_chunk.id"), unique=True)
    text: Mapped[str]

    podcast_chunk: Mapped["PodcastChunk"] = relationship(back_populates="transcript")
