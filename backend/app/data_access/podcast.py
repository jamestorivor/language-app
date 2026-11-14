from math import ceil

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.models.podcast import PodcastChunk, PodcastEpisode, PodcastTranscript


def get_episode_by_audio_location(session: Session, user_id: int, audio_location: str):
    return session.scalar(select(PodcastEpisode).where(
        PodcastEpisode.user_id == user_id, PodcastEpisode.audio_location == audio_location
    ))


def add_episode(session: Session, user_id: int, audio_location: str, title: str, author: str, duration: float, chunk_interval: float, transcript: list[dict] | None = None, language: str = "ja"):
    episode = get_episode_by_audio_location(session, user_id, audio_location)
    if episode is not None:
        return episode
    episode = PodcastEpisode(user_id=user_id, audio_location=audio_location, title=title, author=author, duration=duration, language=language)
    session.add(episode)
    try:
        session.flush()
        chunk_count = ceil(duration / chunk_interval)
        chunk_texts: list[list[str]] = [[] for _ in range(chunk_count)]
        if transcript is not None:
            for snippet in transcript:
                start = snippet["start"]
                if 0 <= start < duration:
                    chunk_texts[int(start // chunk_interval)].append(snippet["text"])
        for index in range(chunk_count):
            start = index * chunk_interval
            end = min((index + 1) * chunk_interval, duration)
            chunk = PodcastChunk(user_id=user_id, podcast_id=episode.id, start_time=start, end_time=end)
            if transcript is not None:
                chunk.transcript = PodcastTranscript(text=" ".join(chunk_texts[index]))
            session.add(chunk)

        session.commit()
    except IntegrityError:
        session.rollback()
        # A concurrent request may have inserted the same audio location.
        episode = get_episode_by_audio_location(session, user_id, audio_location)
        if episode is None:
            raise
    return episode


def get_episode(session: Session, user_id: int, episode_id: int):
    return session.scalar(select(PodcastEpisode).where(
        PodcastEpisode.id == episode_id, PodcastEpisode.user_id == user_id
    ))

def list_user_episodes(session : Session, user_id : int):
    return list(session.scalars(select(PodcastEpisode).where(PodcastEpisode.user_id == user_id)).all())


def delete_episode(session: Session, episode: PodcastEpisode):
    chunk_ids = select(PodcastChunk.id).where(PodcastChunk.podcast_id == episode.id)
    session.execute(delete(PodcastTranscript).where(PodcastTranscript.podcast_chunk_id.in_(chunk_ids)))
    session.execute(delete(PodcastChunk).where(PodcastChunk.podcast_id == episode.id))
    session.delete(episode)
    session.commit()


def create_new_chunk(session: Session, user_id: int, podcast_id: int, start_time: float, end_time: float):
    chunk = PodcastChunk(user_id=user_id, podcast_id=podcast_id, start_time=start_time, end_time=end_time)
    session.add(chunk)
    session.commit()
    return chunk


def get_chunk(session: Session, user_id: int, chunk_id: int):
    return session.scalar(select(PodcastChunk).join(PodcastEpisode, PodcastChunk.podcast_id == PodcastEpisode.id).where(
        PodcastChunk.id == chunk_id, PodcastChunk.user_id == user_id, PodcastEpisode.user_id == user_id
    ).options(selectinload(PodcastChunk.transcript), selectinload(PodcastChunk.episode)))


def list_chunks(session: Session, user_id: int, podcast_id: int):
    return session.scalars(select(PodcastChunk).where(
        PodcastChunk.user_id == user_id, PodcastChunk.podcast_id == podcast_id
    ).options(selectinload(PodcastChunk.transcript), selectinload(PodcastChunk.episode)).order_by(PodcastChunk.start_time, PodcastChunk.id)).all()


def replace_episode_transcript(session: Session, user_id: int, episode_id: int, snippets: list[dict]):
    chunks = list_chunks(session, user_id, episode_id)
    chunk_texts = [[] for _ in chunks]
    for snippet in snippets:
        matching = [index for index, chunk in enumerate(chunks) if chunk.start_time <= snippet["start"] < chunk.end_time]
        if not matching:
            raise HTTPException(status_code=422, detail="A transcript timestamp does not belong to an existing segment.")
        for index in matching:
            chunk_texts[index].append(snippet["text"])
    for chunk, texts in zip(chunks, chunk_texts):
        if chunk.transcript is None:
            chunk.transcript = PodcastTranscript(text=" ".join(texts))
        else:
            chunk.transcript.text = " ".join(texts)


def rebuild_chunks(session: Session, episode: PodcastEpisode, interval: float, snippets: list[dict] | None):
    chunks = list_chunks(session, episode.user_id, episode.id)
    count = ceil(episode.duration / interval)
    texts: list[list[str]] = [[] for _ in range(count)]
    if snippets is not None:
        for snippet in snippets:
            start = snippet["start"]
            if 0 <= start < episode.duration:
                texts[int(start // interval)].append(snippet["text"])
    for chunk in chunks:
        session.delete(chunk)
    # Delete first so no old transcript or segment survives the replacement.
    session.flush()
    for index in range(count):
        chunk = PodcastChunk(user_id=episode.user_id, podcast_id=episode.id,
                             start_time=index * interval, end_time=min((index + 1) * interval, episode.duration))
        if snippets is not None:
            chunk.transcript = PodcastTranscript(text=" ".join(texts[index]))
        session.add(chunk)


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
