import logging

from app.observability import log_event
from youtube_transcript_api import YouTubeTranscriptApi, VideoUnavailable, NoTranscriptFound, TranscriptsDisabled, CouldNotRetrieveTranscript
from fastapi import HTTPException
ytt_api = YouTubeTranscriptApi()

def get_japanese_transcript(video_id : str):
    try:
        fetched_transcript = ytt_api.fetch(video_id, languages=['ja']).to_raw_data()
        return fetched_transcript
    except VideoUnavailable as error:
        log_event(logging.WARNING, "podcast_transcript_failed", provider="youtube", error_type=type(error).__name__)
        raise HTTPException(404, detail="The requested video is unavailable") from error
    except NoTranscriptFound as error:
        log_event(logging.WARNING, "podcast_transcript_failed", provider="youtube", error_type=type(error).__name__)
        raise HTTPException(
            status_code=404,
            detail="This video has no Japanese transcript.",
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