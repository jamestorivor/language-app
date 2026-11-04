from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.models.podcast import PodcastChunk, PodcastEpisode, PodcastTranscript


def get_episode_by_audio_location(session: Session, audio_location: str):
    return session.scalar(select(PodcastEpisode).where(PodcastEpisode.audio_location == audio_location))


def add_episode(session: Session, audio_location: str, title: str, author: str, duration: float):
    episode = get_episode_by_audio_location(session, audio_location)
    if episode is not None:
        return episode
    episode = PodcastEpisode(audio_location=audio_location, title=title, author=author, duration=duration)
    session.add(episode)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # A concurrent request may have inserted the same audio location.
        episode = get_episode_by_audio_location(session, audio_location)
        if episode is None:
            raise
    return episode


def get_episode(session: Session, episode_id: int):
    return session.get(PodcastEpisode, episode_id)


def create_new_chunk(session: Session, user_id: int, podcast_id: int, start_time: float, end_time: float):
    chunk = PodcastChunk(user_id=user_id, podcast_id=podcast_id, start_time=start_time, end_time=end_time)
    session.add(chunk)
    session.commit()
    return chunk


def get_chunk(session: Session, user_id: int, chunk_id: int):
    return session.scalar(select(PodcastChunk).where(
        PodcastChunk.id == chunk_id, PodcastChunk.user_id == user_id
    ).options(selectinload(PodcastChunk.transcript)))


def list_chunks(session: Session, user_id: int, podcast_id: int):
    return session.scalars(select(PodcastChunk).where(
        PodcastChunk.user_id == user_id, PodcastChunk.podcast_id == podcast_id
    ).options(selectinload(PodcastChunk.transcript)).order_by(PodcastChunk.start_time, PodcastChunk.id)).all()


def save_transcript(session: Session, chunk: PodcastChunk, text: str):
    if chunk.transcript is None:
        chunk.transcript = PodcastTranscript(text=text)
    else:
        chunk.transcript.text = text
    session.commit()
    return chunk.transcript


def delete_chunk(session: Session, chunk: PodcastChunk):
    session.delete(chunk)
    session.commit()
