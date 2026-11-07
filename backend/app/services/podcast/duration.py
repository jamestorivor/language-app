"""Look up episode duration from provider metadata, in seconds."""
import math
import os
import re

import requests
from fastapi import HTTPException

from app.schemas import PodcastLink


def parse_youtube_duration(value: str) -> float:
    match = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?", value)
    if not match or not any(match.groups()):
        raise ValueError("Invalid YouTube duration")
    days, hours, minutes, seconds = (float(part or 0) for part in match.groups())
    duration = days * 86400 + hours * 3600 + minutes * 60 + seconds
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid YouTube duration")
    return duration


def get_episode_duration(link: PodcastLink) -> float:
    try:
        if link.provider == "youtube":
            key = os.getenv("YOUTUBE_API_KEY")
            if not key:
                raise HTTPException(status_code=503, detail="YouTube API key is not configured")
            response = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "contentDetails", "id": link.id, "key": key},
                timeout=10,
            )
            response.raise_for_status()
            items = response.json()["items"]
            if not items:
                raise HTTPException(status_code=404, detail="YouTube video not found or unavailable")
            return parse_youtube_duration(items[0]["contentDetails"]["duration"])

        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise HTTPException(status_code=503, detail="Spotify API credentials are not configured")
        token_response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret), timeout=10,
        )
        token_response.raise_for_status()
        token = token_response.json()["access_token"]
        if not re.fullmatch(r"[A-Za-z0-9]+", link.id):
            raise HTTPException(status_code=422, detail="Invalid Spotify episode ID")
        response = requests.get(
            f"https://api.spotify.com/v1/episodes/{link.id}",
            params={"market": os.getenv("SPOTIFY_MARKET", "SG")},
            headers={"Authorization": f"Bearer {token}"}, timeout=10,
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Spotify episode not found or unavailable")
        response.raise_for_status()
        duration = float(response.json()["duration_ms"]) / 1000
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("Invalid Spotify duration")
        return duration
    except HTTPException:
        raise
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError) as exc:
        raise HTTPException(status_code=502, detail="Could not retrieve episode duration from provider") from exc
