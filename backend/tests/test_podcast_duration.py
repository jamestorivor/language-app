import pytest
import requests
from fastapi import HTTPException

from app.schemas import PodcastLink
from app.services.podcast import duration


class Response:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError()

    def json(self):
        return self.data


@pytest.mark.parametrize(("value", "seconds"), [("PT1H2M3S", 3723), ("P1DT1S", 86401), ("PT30S", 30)])
def test_youtube_duration_format(value, seconds):
    assert duration.parse_youtube_duration(value) == seconds


def test_youtube_lookup(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "key")
    monkeypatch.setattr(duration.requests, "get", lambda url, **kwargs: Response({"items": [{"contentDetails": {"duration": "PT2M3S"}}]}))
    assert duration.get_episode_duration(PodcastLink(provider="youtube", id="video")) == 123


def test_spotify_lookup(monkeypatch):
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "secret")
    monkeypatch.setattr(duration.requests, "post", lambda url, **kwargs: Response({"access_token": "token"}))
    def get(url, **kwargs):
        assert url == "https://api.spotify.com/v1/episodes/episode123"
        assert kwargs["params"]["market"] == "SG"
        return Response({"duration_ms": 90500})
    monkeypatch.setattr(duration.requests, "get", get)
    assert duration.get_episode_duration(PodcastLink(provider="spotify", id="episode123")) == 90.5


def test_missing_video(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "key")
    monkeypatch.setattr(duration.requests, "get", lambda url, **kwargs: Response({"items": []}))
    with pytest.raises(HTTPException) as error:
        duration.get_episode_duration(PodcastLink(provider="youtube", id="video"))
    assert error.value.status_code == 404


def test_provider_error_does_not_expose_credentials(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "secret")
    def fail(*args, **kwargs):
        raise requests.ConnectionError("secret")
    monkeypatch.setattr(duration.requests, "get", fail)
    with pytest.raises(HTTPException) as error:
        duration.get_episode_duration(PodcastLink(provider="youtube", id="video"))
    assert error.value.status_code == 502
    assert "secret" not in error.value.detail
