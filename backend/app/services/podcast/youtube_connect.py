import logging
import math
import os

import requests
from fastapi import HTTPException

from app.observability import log_event

TRANSCRIPT_URL = "https://api.freetranscriptapi.com/v1/transcript"


def _failure(status: int, detail: str, reason: str) -> HTTPException:
    log_event(logging.WARNING, "podcast_transcript_failed", provider="freetranscriptapi", error_type=reason)
    return HTTPException(status_code=status, detail=detail)


def get_transcript(video_id: str, language: str):
    api_key = os.getenv("FREETRANSCRIPT_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        response = requests.get(
            TRANSCRIPT_URL,
            params={"video_url": video_id, "lang": language},
            headers=headers,
            timeout=20,
        )
    except requests.Timeout as error:
        raise _failure(504, "The transcript service timed out. Please try again.", "Timeout") from error
    except requests.RequestException as error:
        raise _failure(502, "Could not reach the transcript service. Please try again.", type(error).__name__) from error

    if response.status_code == 404:
        raise _failure(404, "This video is unavailable or has no transcript.", "NotFound")
    if response.status_code == 429:
        raise _failure(503, "The transcript service rate limit was reached. Please try again later.", "RateLimit")
    if response.status_code in (401, 402):
        raise _failure(503, "The transcript service API key or credits need attention.", "AuthenticationOrCredits")
    if response.status_code != 200:
        raise _failure(502, "The transcript service could not process the request. Please try again.", "ProviderError")

    try:
        data = response.json()
    except ValueError as error:
        raise _failure(502, "The transcript service returned an invalid response.", "InvalidResponse") from error

    if not isinstance(data, dict) or not isinstance(data.get("language"), str) or not isinstance(data.get("transcript"), list):
        raise _failure(502, "The transcript service returned an invalid response.", "InvalidResponse")
    # The provider falls back to another language if the requested one is absent.
    if data["language"].lower().replace("_", "-").split("-")[0] != language:
        raise _failure(404, f"This video has no {'English' if language == 'en' else 'Japanese'} transcript.", "LanguageUnavailable")
    if not data["transcript"]:
        raise _failure(404, "This video has no transcript.", "EmptyTranscript")
    for snippet in data["transcript"]:
        if (not isinstance(snippet, dict) or not isinstance(snippet.get("text"), str)
                or isinstance(snippet.get("start"), bool) or not isinstance(snippet.get("start"), (int, float))
                or not math.isfinite(snippet["start"]) or snippet["start"] < 0):
            raise _failure(502, "The transcript service returned an invalid response.", "InvalidResponse")
    return data["transcript"]
