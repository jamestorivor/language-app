from youtube_transcript_api import YouTubeTranscriptApi, VideoUnavailable, NoTranscriptFound, TranscriptsDisabled, CouldNotRetrieveTranscript
from fastapi import HTTPException
ytt_api = YouTubeTranscriptApi()

def get_japanese_transcript(video_id : str):
    try:
        fetched_transcript = ytt_api.fetch(video_id, languages=['ja']).to_raw_data()
        return fetched_transcript
    except VideoUnavailable as error:
        raise HTTPException(404, detail="The requested video is unavailable") from error
    except NoTranscriptFound as error:
        raise HTTPException(
            status_code=404,
            detail="This video has no Japanese transcript.",
        ) from error
    except TranscriptsDisabled as error:
        raise HTTPException(
            status_code=404,
            detail="Transcripts are disabled for this video.",
        ) from error
    except CouldNotRetrieveTranscript as error:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve the transcript. Please try again.",
        ) from error