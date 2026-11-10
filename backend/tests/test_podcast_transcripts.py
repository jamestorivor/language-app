import pytest
import requests
from fastapi import HTTPException

from app.services.podcast import youtube_connect


class Response:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self.data = data

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


@pytest.mark.parametrize("language", ["ja", "en"])
def test_fetch_preserves_caption_timing_and_requested_language(monkeypatch, language):
    monkeypatch.delenv("FREETRANSCRIPT_API_KEY", raising=False)
    captions = [{"text": "example", "start": 12.3, "duration": 2.1}]
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response(data={"language": language, "transcript": captions})

    monkeypatch.setattr(youtube_connect.requests, "get", get)
    assert youtube_connect.get_transcript("video123", language) == captions
    assert calls == [(youtube_connect.TRANSCRIPT_URL, {
        "params": {"video_url": "video123", "lang": language}, "headers": {}, "timeout": 20,
    })]


def test_api_key_is_sent_only_as_authorization_header(monkeypatch):
    monkeypatch.setenv("FREETRANSCRIPT_API_KEY", "example-key")
    calls = []
    def get(url, **kwargs):
        calls.append(kwargs)
        return Response(data={"language": "en-US", "transcript": [{"text": "hello", "start": 0}]})
    monkeypatch.setattr(youtube_connect.requests, "get", get)

    assert youtube_connect.get_transcript("video123", "en")[0]["text"] == "hello"
    assert calls[0]["headers"] == {"Authorization": "Bearer example-key"}
    assert calls[0]["params"] == {"video_url": "video123", "lang": "en"}


def test_other_language_fallback_is_rejected(monkeypatch):
    monkeypatch.setattr(youtube_connect.requests, "get", lambda *args, **kwargs: Response(
        data={"language": "en", "transcript": [{"text": "hello", "start": 0}]}
    ))
    with pytest.raises(HTTPException) as error:
        youtube_connect.get_transcript("video123", "ja")
    assert error.value.status_code == 404
    assert "Japanese" in error.value.detail


@pytest.mark.parametrize(("provider_status", "expected_status"), [(404, 404), (429, 503), (401, 503), (402, 503), (500, 502)])
def test_provider_errors_do_not_return_a_transcript(monkeypatch, provider_status, expected_status):
    monkeypatch.setattr(youtube_connect.requests, "get", lambda *args, **kwargs: Response(provider_status))
    with pytest.raises(HTTPException) as error:
        youtube_connect.get_transcript("video123", "en")
    assert error.value.status_code == expected_status


@pytest.mark.parametrize("payload", [ValueError("invalid JSON"), {}, {"language": "en", "transcript": "text"},
    {"language": "en", "transcript": [{"text": "hi", "start": "1"}]},
    {"language": "en", "transcript": [{"text": "hi", "start": float("nan")}]},
    {"language": "en", "transcript": [{"text": "hi", "start": -1}]},
])
def test_malformed_provider_response_is_rejected(monkeypatch, payload):
    monkeypatch.setattr(youtube_connect.requests, "get", lambda *args, **kwargs: Response(data=payload))
    with pytest.raises(HTTPException) as error:
        youtube_connect.get_transcript("video123", "en")
    assert error.value.status_code == 502


@pytest.mark.parametrize(("exception", "status"), [(requests.Timeout(), 504), (requests.ConnectionError(), 502)])
def test_network_errors_are_reported(monkeypatch, exception, status):
    def fail(*args, **kwargs):
        raise exception
    monkeypatch.setattr(youtube_connect.requests, "get", fail)
    with pytest.raises(HTTPException) as error:
        youtube_connect.get_transcript("video123", "en")
    assert error.value.status_code == status
