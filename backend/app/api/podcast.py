from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.services.podcast.youtube_connect import get_transcript
from app.services.podcast.duration import get_episode_duration
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
        return existing
    duration = get_episode_duration(request.podcast_details)
    if request.chunk_interval < duration / 10000:
        raise HTTPException(status_code=422, detail="An episode can have at most 10000 generated chunks")
    transcript = (
        get_transcript(request.podcast_details.id, request.language)
        if request.podcast_details.provider == "youtube"
        else None
    )
    episode = data.add_episode(db, DEVELOPMENT_USER_ID, duration=duration, transcript=transcript, **request.model_dump(exclude={"podcast_details"}))
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


@router.patch("/{episode_id}", response_model=PodcastEpisodeResponse)
def update_episode(episode_id: int, request: PodcastEpisodeUpdate, db: Session = Depends(get_db)):
    episode = data.get_episode(db, DEVELOPMENT_USER_ID, episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
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
