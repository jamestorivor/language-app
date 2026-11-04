from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PodcastEpisode(Base):
    __tablename__ = "podcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    audio_location: Mapped[str] = mapped_column(unique=True, nullable=False)
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

    transcript: Mapped["PodcastTranscript | None"] = relationship(
        back_populates="podcast_chunk", cascade="all, delete-orphan", uselist=False
    )


class PodcastTranscript(Base):
    __tablename__ = "podcast_transcript"

    id: Mapped[int] = mapped_column(primary_key=True)
    podcast_chunk_id: Mapped[int] = mapped_column(ForeignKey("podcast_chunk.id"), unique=True)
    text: Mapped[str]

    podcast_chunk: Mapped["PodcastChunk"] = relationship(back_populates="transcript")
