from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from urllib.parse import parse_qs, urlparse
import re

from app.services.podcast.youtube_connect import get_transcript
from app.services.podcast.duration import get_episode_duration
from app.services.podcast.external_transcript import parse_external_transcript
from app.data_access import podcast as data
from app.db.session import get_db
from app.config import DEVELOPMENT_USER_ID
from app.schemas import PodcastChunkCreate, PodcastChunkResponse, PodcastEpisodeCreate, PodcastEpisodeUpdate, PodcastEpisodeResponse, PodcastTranscriptCreate, PodcastTranscriptResponse

router = APIRouter(prefix="/podcasts", tags=["podcasts"])


@router.post("", response_model=PodcastEpisodeResponse)
def create_episode(request: PodcastEpisodeCreate, db: Session = Depends(get_db)):
    existing = data.get_episode_by_audio_location(db, DEVELOPMENT_USER_ID, request.audio_location)
    if existing is not None:
        if existing.language != request.language:
            raise HTTPException(status_code=409, detail="This podcast is already in your library with a different language. Edit its details to change the language.")
        if request.external_transcript is not None:
            raise HTTPException(status_code=409, detail="This podcast is already in your library. Edit it to add or replace its transcript.")
        return existing
    duration = get_episode_duration(request.podcast_details)
    if request.chunk_interval < duration / 10000:
        raise HTTPException(status_code=422, detail="An episode can have at most 10000 generated chunks")
    transcript = (
        parse_external_transcript(request.external_transcript, duration, file_format=request.external_transcript_format)
        if request.external_transcript is not None
        else get_transcript(request.podcast_details.id, request.language)
        if request.podcast_details.provider == "youtube"
        else None
    )
    episode = data.add_episode(db, DEVELOPMENT_USER_ID, duration=duration, transcript=transcript, **request.model_dump(exclude={"podcast_details", "external_transcript", "external_transcript_format"}))
    if episode.language != request.language:
        raise HTTPException(status_code=409, detail="This podcast is already in your library with a different language. Edit its details to change the language.")
    return episode

@router.get("", response_model=list[PodcastEpisodeResponse])
def read_all_episodes(db : Session = Depends(get_db)):
    return data.list_user_episodes(db, DEVELOPMENT_USER_ID)


@router.get("/{episode_id}", response_model=PodcastEpisodeResponse)
def read_episode(episode_id: int, db: Session = Depends(get_db)):
    episode = data.get_episode(db, DEVELOPMENT_USER_ID, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


@router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_episode(episode_id: int, db: Session = Depends(get_db)):
    episode = data.get_episode(db, DEVELOPMENT_USER_ID, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    data.delete_episode(db, episode)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{episode_id}", response_model=PodcastEpisodeResponse)
def update_episode(episode_id: int, request: PodcastEpisodeUpdate, db: Session = Depends(get_db)):
    episode = data.get_episode(db, DEVELOPMENT_USER_ID, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    if request.refresh_youtube_transcript and (request.chunk_interval is None or request.external_transcript is not None):
        raise HTTPException(status_code=422, detail="Choose one transcript source when updating segment times.")
    if request.chunk_interval is not None:
        if request.chunk_interval < episode.duration / 10000:
            raise HTTPException(status_code=422, detail="An episode can have at most 10000 generated chunks")
        chunks = data.list_chunks(db, DEVELOPMENT_USER_ID, episode_id)
        if request.external_transcript is not None:
            transcript = parse_external_transcript(request.external_transcript, episode.duration, require_timestamps=True, file_format=request.external_transcript_format)
        elif request.refresh_youtube_transcript:
            url = urlparse(episode.audio_location)
            if url.scheme == "https" and url.hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"} and url.path == "/watch":
                video_id = parse_qs(url.query).get("v", [""])[0]
            elif url.scheme == "https" and url.hostname == "youtu.be":
                video_id = url.path.lstrip("/")
            else:
                video_id = ""
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                raise HTTPException(status_code=422, detail="YouTube captions are unavailable for this podcast link.")
            transcript = get_transcript(video_id, request.language or episode.language)
        elif any(chunk.transcript and chunk.transcript.text.strip() for chunk in chunks):
            raise HTTPException(status_code=422, detail="Upload a timestamped transcript or choose YouTube captions to update segment times.")
        else:
            transcript = [] if any(chunk.transcript is not None for chunk in chunks) else None
        data.rebuild_chunks(db, episode, request.chunk_interval, transcript)
    elif request.external_transcript is not None:
        transcript = parse_external_transcript(request.external_transcript, episode.duration, file_format=request.external_transcript_format)
        data.replace_episode_transcript(db, DEVELOPMENT_USER_ID, episode_id, transcript)
    episode.title = request.title
    episode.author = request.author
    if request.language is not None:
        episode.language = request.language
    db.commit()
    db.refresh(episode)
    return episode


@router.post("/{episode_id}/chunks", response_model=PodcastChunkResponse, status_code=status.HTTP_201_CREATED)
def create_chunk(episode_id: int, request: PodcastChunkCreate, db: Session = Depends(get_db)):
    episode = data.get_episode(db, DEVELOPMENT_USER_ID, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    if request.end_time > episode.duration:
        raise HTTPException(status_code=422, detail="Chunk end time exceeds episode duration")
    return data.create_new_chunk(db, DEVELOPMENT_USER_ID, episode_id, request.start_time, request.end_time)


@router.get("/{episode_id}/chunks", response_model=list[PodcastChunkResponse])
def read_chunks(episode_id: int, db: Session = Depends(get_db)):
    if data.get_episode(db, DEVELOPMENT_USER_ID, episode_id) is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return data.list_chunks(db, DEVELOPMENT_USER_ID, episode_id)


def owned_chunk(db: Session, chunk_id: int):
    chunk = data.get_chunk(db, DEVELOPMENT_USER_ID, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk


@router.get("/chunks/{chunk_id}", response_model=PodcastChunkResponse)
def read_chunk(chunk_id: int, db: Session = Depends(get_db)):
    return owned_chunk(db, chunk_id)


@router.put("/chunks/{chunk_id}/transcript", response_model=PodcastTranscriptResponse)
def put_transcript(chunk_id: int, request: PodcastTranscriptCreate, db: Session = Depends(get_db)):
    return data.save_transcript(db, owned_chunk(db, chunk_id), request.text)


@router.delete("/chunks/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chunk(chunk_id: int, db: Session = Depends(get_db)):
    data.delete_chunk(db, owned_chunk(db, chunk_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
