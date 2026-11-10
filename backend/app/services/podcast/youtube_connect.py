import logging
import os

from app.observability import log_event
from youtube_transcript_api import YouTubeTranscriptApi, VideoUnavailable, NoTranscriptFound, TranscriptsDisabled, CouldNotRetrieveTranscript
from youtube_transcript_api.proxies import WebshareProxyConfig
from fastapi import HTTPException


def youtube_api():
    username = os.getenv("WEBSHARE_PROXY_USERNAME")
    password = os.getenv("WEBSHARE_PROXY_PASSWORD")
    if bool(username) != bool(password):
        log_event(logging.ERROR, "podcast_transcript_proxy_misconfigured", provider="youtube")
        raise HTTPException(503, detail="YouTube transcript proxy is not configured correctly.")
    if username and password:
        return YouTubeTranscriptApi(proxy_config=WebshareProxyConfig(
            proxy_username=username,
            proxy_password=password,
        ))
    return YouTubeTranscriptApi()

def get_transcript(video_id: str, language: str):
    try:
        fetched_transcript = youtube_api().fetch(video_id, languages=[language]).to_raw_data()
        return fetched_transcript
    except VideoUnavailable as error:
        log_event(logging.WARNING, "podcast_transcript_failed", provider="youtube", error_type=type(error).__name__)
        raise HTTPException(404, detail="The requested video is unavailable") from error
    except NoTranscriptFound as error:
        log_event(logging.WARNING, "podcast_transcript_failed", provider="youtube", error_type=type(error).__name__)
        raise HTTPException(
            status_code=404,
            detail=f"This video has no {'English' if language == 'en' else 'Japanese'} transcript.",
        ) from error
    except TranscriptsDisabled as error:
        log_event(logging.WARNING, "podcast_transcript_failed", provider="youtube", error_type=type(error).__name__)
        raise HTTPException(
            status_code=404,
            detail="Transcripts are disabled for this video.",
        ) from error
    except CouldNotRetrieveTranscript as error:
        log_event(logging.WARNING, "podcast_transcript_failed", provider="youtube", error_type=type(error).__name__)
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve the transcript. Please try again.",
        ) from error
