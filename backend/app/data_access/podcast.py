from math import ceil, isfinite
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.models.podcast import PodcastChunk, PodcastEpisode, PodcastTranscript
from app.services.podcast.vocabulary import reset_baseline


def _transcript_data(snippets: list[dict]) -> tuple[str, list[dict]]:
    """Join source cues while retaining their exact code-point spans and times."""
    parts: list[str] = []
    cues: list[dict] = []
    offset = 0
    for snippet in snippets:
        value = snippet["text"]
        if parts:
            offset += 1
        start_idx = offset
        offset += len(value)
        parts.append(value)
        if snippet.get("timed", True) is False:
            continue
        start = snippet.get("start")
        if isinstance(start, bool) or not isinstance(start, (int, float)) or not isfinite(start) or start < 0:
            continue
        end = snippet.get("end")
        if end is None:
            duration = snippet.get("duration")
            if not isinstance(duration, bool) and isinstance(duration, (int, float)) and isfinite(duration) and duration > 0:
                end = start + duration
        if isinstance(end, bool) or not isinstance(end, (int, float)) or not isfinite(end) or end <= start:
            end = None
        cues.append({"id": str(uuid4()), "start_idx": start_idx, "end_idx": offset,
                     "start_ms": round(start * 1000), "end_ms": round(end * 1000) if end is not None else None})
    return " ".join(parts), cues


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
        chunk_texts: list[list[dict]] = [[] for _ in range(chunk_count)]
        if transcript is not None:
            for snippet in transcript:
                start = snippet["start"]
                if 0 <= start < duration:
                    chunk_texts[int(start // chunk_interval)].append(snippet)
        for index in range(chunk_count):
            start = index * chunk_interval
            end = min((index + 1) * chunk_interval, duration)
            chunk = PodcastChunk(user_id=user_id, podcast_id=episode.id, start_time=start, end_time=end)
            if transcript is not None:
                joined, cues = _transcript_data(chunk_texts[index])
                chunk.transcript = PodcastTranscript(text=joined, cues=cues)
            session.add(chunk)

        if transcript and any(item["text"].strip() for item in transcript):
            reset_baseline(session, episode, True)
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
            chunk_texts[index].append(snippet)
    for chunk, texts in zip(chunks, chunk_texts):
        joined, cues = _transcript_data(texts)
        if chunk.transcript is None:
            chunk.transcript = PodcastTranscript(text=joined, cues=cues)
        else:
            chunk.transcript.text = joined
            chunk.transcript.cues = cues


def rebuild_chunks(session: Session, episode: PodcastEpisode, interval: float, snippets: list[dict] | None):
    chunks = list_chunks(session, episode.user_id, episode.id)
    count = ceil(episode.duration / interval)
    texts: list[list[dict]] = [[] for _ in range(count)]
    if snippets is not None:
        for snippet in snippets:
            start = snippet["start"]
            if 0 <= start < episode.duration:
                texts[int(start // interval)].append(snippet)
    for chunk in chunks:
        session.delete(chunk)
    # Delete first so no old transcript or segment survives the replacement.
    session.flush()
    for index in range(count):
        chunk = PodcastChunk(user_id=episode.user_id, podcast_id=episode.id,
                             start_time=index * interval, end_time=min((index + 1) * interval, episode.duration))
        if snippets is not None:
            joined, cues = _transcript_data(texts[index])
            chunk.transcript = PodcastTranscript(text=joined, cues=cues)
        session.add(chunk)


def save_transcript(session: Session, chunk: PodcastChunk, text: str):
    if chunk.transcript is None:
        chunk.transcript = PodcastTranscript(text=text, cues=[])
    else:
        if chunk.transcript.text != text:
            chunk.transcript.cues = []
        chunk.transcript.text = text
    session.flush()
    chunks = list_chunks(session, chunk.user_id, chunk.podcast_id)
    reset_baseline(session, chunk.episode, any(c.transcript and c.transcript.text.strip() for c in chunks))
    session.commit()
    return chunk.transcript


def delete_chunk(session: Session, chunk: PodcastChunk):
    session.delete(chunk)
    session.commit()
