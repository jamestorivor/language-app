import pytest

from app.services.podcast import youtube_connect


@pytest.mark.parametrize("language", ["ja", "en"])
def test_youtube_fetch_requests_the_selected_language(monkeypatch, language):
    calls = []

    class Transcript:
        def to_raw_data(self):
            return [{"text": "example", "start": 0}]

    def fetch(video_id, languages):
        calls.append((video_id, languages))
        return Transcript()

    monkeypatch.setattr(youtube_connect, "youtube_api", lambda: type("Api", (), {"fetch": staticmethod(fetch)})())
    assert youtube_connect.get_transcript("video", language) == [{"text": "example", "start": 0}]
    assert calls == [("video", [language])]


def test_youtube_api_uses_webshare_when_configured(monkeypatch):
    monkeypatch.setenv("WEBSHARE_PROXY_USERNAME", "example-user")
    monkeypatch.setenv("WEBSHARE_PROXY_PASSWORD", "example-password")
    monkeypatch.setattr(youtube_connect, "YouTubeTranscriptApi", lambda **kwargs: kwargs)

    api = youtube_connect.youtube_api()

    assert isinstance(api["proxy_config"], youtube_connect.WebshareProxyConfig)
    assert api["proxy_config"].proxy_username == "example-user"
    assert api["proxy_config"].proxy_password == "example-password"


def test_youtube_api_uses_direct_connection_without_proxy(monkeypatch):
    monkeypatch.delenv("WEBSHARE_PROXY_USERNAME", raising=False)
    monkeypatch.delenv("WEBSHARE_PROXY_PASSWORD", raising=False)
    monkeypatch.setattr(youtube_connect, "YouTubeTranscriptApi", lambda **kwargs: kwargs)

    assert youtube_connect.youtube_api() == {}


@pytest.mark.parametrize("missing", ["WEBSHARE_PROXY_USERNAME", "WEBSHARE_PROXY_PASSWORD"])
def test_youtube_api_rejects_incomplete_proxy_configuration(monkeypatch, missing):
    monkeypatch.setenv("WEBSHARE_PROXY_USERNAME", "example-user")
    monkeypatch.setenv("WEBSHARE_PROXY_PASSWORD", "example-password")
    monkeypatch.delenv(missing)

    with pytest.raises(youtube_connect.HTTPException) as error:
        youtube_connect.youtube_api()
    assert error.value.status_code == 503
