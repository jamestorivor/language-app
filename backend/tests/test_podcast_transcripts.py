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

    monkeypatch.setattr(youtube_connect.ytt_api, "fetch", fetch)
    assert youtube_connect.get_transcript("video", language) == [{"text": "example", "start": 0}]
    assert calls == [("video", [language])]
