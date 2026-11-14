import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models.podcast import (PodcastChunk, PodcastEpisode, PodcastTranscript,
                                   PodcastVocabularyBaseline, PodcastVocabularyAnalysis)
from app.db.models.user import User
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("app.api.podcast.get_episode_duration", lambda url: 60.0)
    monkeypatch.setattr("app.api.podcast.get_transcript", lambda video_id, language: [])
    monkeypatch.setattr("app.services.podcast.vocabulary.ratings", lambda *args: {})
    monkeypatch.setattr("app.services.podcast.vocabulary.ratings", lambda session, user_id, language: {})
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    for model in (User, PodcastEpisode, PodcastChunk, PodcastTranscript, PodcastVocabularyBaseline, PodcastVocabularyAnalysis):
        model.__table__.create(engine)
    with Session(engine) as session:
        session.add_all([User(id=1, name="Test"), User(id=2, name="Other")])
        session.commit()

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_episode_and_chunk_lifecycle(client):
    episode = {"audio_location": "https://example.com/audio", "title": "Episode", "author": "Author", "chunk_interval": 20,
        "podcast_details": {"provider": "youtube", "id": "test"}, "podcast_details": {"provider": "youtube", "id": "test"}}
    first = client.post('/podcasts', json=episode)
    assert first.status_code == 200
    episode_id = first.json()['id']
    assert client.post('/podcasts', json={**episode, 'title': 'Other'}).json() == first.json()
    generated = client.get(f'/podcasts/{episode_id}/chunks').json()
    assert all((chunk['episode_title'], chunk['episode_author']) == ('Episode', 'Author') for chunk in generated)
    assert [(chunk['start_time'], chunk['end_time']) for chunk in generated] == [(0, 20), (20, 40), (40, 60)]
    assert client.get(f'/podcasts/{episode_id}').json() == first.json()
    assert client.post(f'/podcasts/{episode_id}/chunks', json={'start_time': 10, 'end_time': 61}).status_code == 422
    assert client.post(f'/podcasts/{episode_id}/chunks', json={'start_time': 10, 'end_time': 10}).status_code == 422
    chunk = client.post(f'/podcasts/{episode_id}/chunks', json={'start_time': 10, 'end_time': 20})
    assert chunk.status_code == 201
    assert (chunk.json()['episode_title'], chunk.json()['episode_author']) == ('Episode', 'Author')
    chunk_id = chunk.json()['id']
    assert client.get(f'/podcasts/chunks/{chunk_id}').json()['episode_title'] == 'Episode'
    assert client.put(f'/podcasts/chunks/{chunk_id}/transcript', json={'text': 'first'}).json()['text'] == 'first'
    assert client.put(f'/podcasts/chunks/{chunk_id}/transcript', json={'text': 'updated'}).json()['text'] == 'updated'
    chunks = client.get(f'/podcasts/{episode_id}/chunks').json()
    assert next(item for item in chunks if item['id'] == chunk_id)['transcript']['text'] == 'updated'
    assert client.delete(f'/podcasts/chunks/{chunk_id}').status_code == 204
    assert client.get(f'/podcasts/chunks/{chunk_id}').status_code == 404
    assert len(client.get(f'/podcasts/{episode_id}/chunks').json()) == 3


def test_update_segment_length_rebuilds_transcripts_and_details(client):
    episode_id = client.post('/podcasts', json={
        'audio_location': 'audio', 'title': 'Before', 'author': 'Author',
        'chunk_interval': 20, 'podcast_details': {'provider': 'spotify', 'id': 'episode'},
        'external_transcript': '[00:05] First\n[00:25] Second\n[00:45] Third',
    }).json()['id']
    update = {'title': 'After', 'author': 'Author', 'chunk_interval': 30,
              'external_transcript': '[00:05] First\n[00:25] Second\n[00:45] Third'}
    assert client.patch(f'/podcasts/{episode_id}', json=update).status_code == 200
    chunks = client.get(f'/podcasts/{episode_id}/chunks').json()
    assert [(c['start_time'], c['end_time'], c['transcript']['text']) for c in chunks] == [
        (0, 30, 'First Second'), (30, 60, 'Third')]
    assert all(c['episode_title'] == 'After' for c in chunks)


def test_segment_rebuild_rejects_missing_or_invalid_transcript_without_changes(client):
    episode_id = client.post('/podcasts', json={
        'audio_location': 'audio', 'title': 'Before', 'author': 'Author',
        'chunk_interval': 20, 'podcast_details': {'provider': 'spotify', 'id': 'episode'},
        'external_transcript': '[00:05] Existing',
    }).json()['id']
    original = client.get(f'/podcasts/{episode_id}/chunks').json()
    for extra in ({}, {'external_transcript': 'Untimed text'},
                  {'external_transcript': '[01:00] Outside'}, {'chunk_interval': 0},
                  {'chunk_interval': 0.001}):
        response = client.patch(f'/podcasts/{episode_id}', json={
            'title': 'After', 'author': 'Author', 'chunk_interval': 30, **extra})
        assert response.status_code == 422
        assert client.get(f'/podcasts/{episode_id}/chunks').json() == original
        assert client.get(f'/podcasts/{episode_id}').json()['title'] == 'Before'


def test_rebuild_uses_requested_youtube_captions_and_preserves_on_failure(client, monkeypatch):
    from fastapi import HTTPException

    episode_id = client.post('/podcasts', json={
        'audio_location': 'https://youtu.be/abcdefghijk', 'title': 'Before', 'author': 'Author',
        'chunk_interval': 20, 'podcast_details': {'provider': 'youtube', 'id': 'abcdefghijk'},
        'external_transcript': '[00:05] Uploaded',
    }).json()['id']
    update = {'title': 'After', 'author': 'Author', 'language': 'en', 'chunk_interval': 30,
              'refresh_youtube_transcript': True}
    original = client.get(f'/podcasts/{episode_id}/chunks').json()
    def fail(*args):
        raise HTTPException(status_code=503, detail='Unavailable')
    monkeypatch.setattr('app.api.podcast.get_transcript', fail)
    assert client.patch(f'/podcasts/{episode_id}', json=update).status_code == 503
    assert client.get(f'/podcasts/{episode_id}/chunks').json() == original
    assert client.get(f'/podcasts/{episode_id}').json()['title'] == 'Before'
    calls = []
    monkeypatch.setattr('app.api.podcast.get_transcript', lambda video, language: calls.append((video, language)) or [
        {'start': 5, 'text': 'First'}, {'start': 31, 'text': 'Second'}])
    assert client.patch(f'/podcasts/{episode_id}', json=update).status_code == 200
    assert calls == [('abcdefghijk', 'en')]
    assert [chunk['transcript']['text'] for chunk in client.get(f'/podcasts/{episode_id}/chunks').json()] == ['First', 'Second']


def test_rebuild_without_transcript_and_other_user_access(client):
    episode_id = client.post('/podcasts', json={
        'audio_location': 'audio', 'title': 'Episode', 'author': 'Author',
        'chunk_interval': 20, 'podcast_details': {'provider': 'spotify', 'id': 'episode'},
    }).json()['id']
    response = client.patch(f'/podcasts/{episode_id}', json={
        'title': 'Episode', 'author': 'Author', 'chunk_interval': 25})
    assert response.status_code == 200
    chunks = client.get(f'/podcasts/{episode_id}/chunks').json()
    assert [(c['start_time'], c['end_time'], c['transcript']) for c in chunks] == [
        (0, 25, None), (25, 50, None), (50, 60, None)]
    with next(iter(app.dependency_overrides[get_db]())) as session:
        other = PodcastEpisode(user_id=2, audio_location='other', title='Other', author='Author', duration=60)
        session.add(other)
        session.commit()
        other_id = other.id
    assert client.patch(f'/podcasts/{other_id}', json={
        'title': 'Changed', 'author': 'Author', 'chunk_interval': 30}).status_code == 404


def test_delete_episode_removes_segments_and_transcripts(client):
    payload = {
        'audio_location': 'delete-audio', 'title': 'Episode', 'author': 'Author',
        'chunk_interval': 20, 'podcast_details': {'provider': 'youtube', 'id': 'test'},
    }
    episode_id = client.post('/api/podcasts', json=payload).json()['id']
    kept_id = client.post('/api/podcasts', json={**payload, 'audio_location': 'keep-audio'}).json()['id']
    chunk_ids = [chunk['id'] for chunk in client.get(f'/api/podcasts/{episode_id}/chunks').json()]
    assert len(chunk_ids) == 3
    assert client.delete(f'/api/podcasts/{episode_id}').status_code == 204
    assert client.get(f'/podcasts/{episode_id}').status_code == 404
    assert [episode['id'] for episode in client.get('/podcasts').json()] == [kept_id]
    assert client.delete(f'/podcasts/{episode_id}').status_code == 404
    with next(iter(app.dependency_overrides[get_db]())) as session:
        assert session.query(PodcastChunk).filter(PodcastChunk.id.in_(chunk_ids)).count() == 0
        assert session.query(PodcastTranscript).filter(PodcastTranscript.podcast_chunk_id.in_(chunk_ids)).count() == 0
        assert session.query(PodcastChunk).count() == 3
        assert session.query(PodcastTranscript).count() == 3
    assert client.post('/podcasts', json=payload).status_code == 200


def test_public_api_prefix_preserves_podcast_routes(client):
    payload = {'audio_location': 'https://example.com/prefixed', 'title': 'Episode',
               'author': 'Author', 'chunk_interval': 20,
               'podcast_details': {'provider': 'youtube', 'id': 'test'}}
    created = client.post('/api/podcasts', json=payload)
    assert created.status_code == 200
    episode_id = created.json()['id']
    assert client.get(f'/api/podcasts/{episode_id}').json()['title'] == 'Episode'
    assert len(client.get(f'/api/podcasts/{episode_id}/chunks').json()) == 3


def test_update_episode_details(client):
    created = client.post('/podcasts', json={
        'audio_location': 'https://example.com/edit', 'title': 'Before', 'author': 'Old',
        'chunk_interval': 20, 'podcast_details': {'provider': 'youtube', 'id': 'test'},
    }).json()
    episode_id = created['id']
    assert client.patch(f'/podcasts/{episode_id}', json={'title': ' ', 'author': 'New'}).status_code == 422
    updated = client.patch(f'/podcasts/{episode_id}', json={'title': ' After ', 'author': ' New '})
    assert updated.status_code == 200
    assert (updated.json()['title'], updated.json()['author']) == ('After', 'New')
    assert client.get(f'/podcasts/{episode_id}').json()['title'] == 'After'
    chunk = client.get(f'/podcasts/{episode_id}/chunks').json()[0]
    assert (chunk['episode_title'], chunk['episode_author']) == ('After', 'New')
    assert client.patch('/podcasts/999999', json={'title': 'After', 'author': 'New'}).status_code == 404
    assert client.post('/podcasts/999/chunks', json={'start_time': 0, 'end_time': 1}).status_code == 404


def test_chunks_are_scoped_to_current_user(client):
    episode_id = client.post('/podcasts', json={
        'audio_location': 'audio', 'title': 'Episode', 'author': 'Author', 'chunk_interval': 60, 'podcast_details': {'provider': 'youtube', 'id': 'test'}
    }).json()['id']
    with next(iter(app.dependency_overrides[get_db]())) as session:
        other = PodcastChunk(user_id=2, podcast_id=episode_id, start_time=0, end_time=1)
        session.add(other)
        session.commit()
        other_id = other.id
    assert all(chunk['user_id'] == 1 for chunk in client.get(f'/podcasts/{episode_id}/chunks').json())
    assert client.get(f'/podcasts/chunks/{other_id}').status_code == 404
    assert client.put(f'/podcasts/chunks/{other_id}/transcript', json={'text': 'text'}).status_code == 404
    assert client.delete(f'/podcasts/chunks/{other_id}').status_code == 404


def test_episodes_are_scoped_to_current_user(client):
    episode = {'audio_location': 'shared-audio', 'title': 'Episode', 'author': 'Author', 'duration': 60}
    with next(iter(app.dependency_overrides[get_db]())) as session:
        other_episode = PodcastEpisode(user_id=2, **episode)
        session.add(other_episode)
        session.commit()
        other_id = other_episode.id
        # A legacy inconsistent chunk must not expose another user's episode.
        chunk = PodcastChunk(user_id=1, podcast_id=other_id, start_time=0, end_time=1)
        session.add(chunk)
        session.commit()
        chunk_id = chunk.id

    assert client.get(f'/podcasts/{other_id}').status_code == 404
    assert client.delete(f'/podcasts/{other_id}').status_code == 404
    assert client.get(f'/podcasts/{other_id}/chunks').status_code == 404
    assert client.post(f'/podcasts/{other_id}/chunks', json={'start_time': 0, 'end_time': 1}).status_code == 404
    assert client.get(f'/podcasts/chunks/{chunk_id}').status_code == 404
    assert client.put(f'/podcasts/chunks/{chunk_id}/transcript', json={'text': 'text'}).status_code == 404
    assert client.delete(f'/podcasts/chunks/{chunk_id}').status_code == 404

    episode['chunk_interval'] = 60
    episode['podcast_details'] = {'provider': 'youtube', 'id': 'test'}
    created = client.post('/podcasts', json=episode)
    assert created.status_code == 200
    assert created.json()['user_id'] == 1
    assert created.json()['id'] != other_id
    assert client.post('/podcasts', json=episode).json() == created.json()


@pytest.mark.parametrize(('duration', 'interval', 'expected'), [
    (65, 30, [(0, 30), (30, 60), (60, 65)]),
    (10, 30, [(0, 10)]),
    (1, 0.25, [(0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1)]),
])
def test_generated_chunks_cover_episode(client, duration, interval, expected, monkeypatch):
    monkeypatch.setattr('app.api.podcast.get_episode_duration', lambda url: duration)
    response = client.post('/podcasts', json={
        'audio_location': 'audio', 'title': 'Episode', 'author': 'Author',
        'chunk_interval': interval, 'podcast_details': {'provider': 'youtube', 'id': 'test'},
    })
    assert response.status_code == 200
    chunks = client.get(f"/podcasts/{response.json()['id']}/chunks").json()
    assert [(chunk['start_time'], chunk['end_time']) for chunk in chunks] == expected


@pytest.mark.parametrize('interval', [0, -1, 0.000001])
def test_invalid_chunk_intervals(client, interval):
    response = client.post('/podcasts', json={
        'audio_location': 'audio', 'title': 'Episode', 'author': 'Author',
        'chunk_interval': interval, 'podcast_details': {'provider': 'youtube', 'id': 'test'},
    })
    assert response.status_code == 422



@pytest.mark.parametrize("details", [
    {"provider": "youtube", "id": "video-id"},
    {"provider": "spotify", "id": "episode-id"},
])
def test_podcast_link_providers(client, details):
    response = client.post("/podcasts", json={
        "audio_location": "audio", "title": "Episode", "author": "Author",
        "chunk_interval": 60, "podcast_details": details,
    })
    assert response.status_code == 200


@pytest.mark.parametrize("details", [None, {"provider": "other", "id": "id"}, {"provider": "youtube", "id": ""}])
def test_invalid_podcast_link(client, details):
    response = client.post("/podcasts", json={
        "audio_location": "audio", "title": "Episode", "author": "Author",
        "chunk_interval": 60, "podcast_details": details,
    })
    assert response.status_code == 422


def test_youtube_transcript_is_saved_by_start_time(client, monkeypatch):
    calls = []
    def get_transcript(video_id, language):
        calls.append((video_id, language))
        return [
            {"text": "first", "start": 0.0, "duration": 2.0},
            {"text": "crosses boundary", "start": 19.5, "duration": 2.0},
            {"text": "next", "start": 20.0, "duration": 1.0},
            {"text": "outside", "start": 60.0, "duration": 1.0},
        ]
    monkeypatch.setattr("app.api.podcast.get_transcript", get_transcript)
    episode = client.post("/podcasts", json={
        "audio_location": "audio", "title": "Episode", "author": "Author",
        "chunk_interval": 20, "podcast_details": {"provider": "youtube", "id": "video123"},
    })
    assert episode.status_code == 200
    chunks = client.get(f"/podcasts/{episode.json()['id']}/chunks").json()
    assert calls == [("video123", "ja")]
    assert [chunk["transcript"]["text"] for chunk in chunks] == ["first crosses boundary", "next", ""]


def test_transcript_fetch_failure_does_not_save_episode(client, monkeypatch):
    from fastapi import HTTPException
    def fail(_video_id, _language):
        raise HTTPException(status_code=404, detail="No transcript")
    monkeypatch.setattr("app.api.podcast.get_transcript", fail)
    response = client.post("/podcasts", json={
        "audio_location": "audio", "title": "Episode", "author": "Author",
        "chunk_interval": 20, "podcast_details": {"provider": "youtube", "id": "video123"},
    })
    assert response.status_code == 404
    assert client.get("/podcasts").json() == []


def test_podcast_language_is_persisted_and_returned_for_segments(client, monkeypatch):
    calls = []
    monkeypatch.setattr("app.api.podcast.get_transcript", lambda video_id, language: calls.append((video_id, language)) or [{"text": "Hello", "start": 0}])
    payload = {"audio_location": "english-audio", "title": "English", "author": "Author", "chunk_interval": 60,
               "podcast_details": {"provider": "youtube", "id": "video"}, "language": "en"}
    response = client.post("/podcasts", json=payload)
    assert response.status_code == 200
    episode = response.json()
    assert episode["language"] == "en"
    assert calls == [("video", "en")]
    assert client.get("/podcasts").json()[0]["language"] == "en"
    assert client.get(f"/podcasts/{episode['id']}").json()["language"] == "en"
    segment = client.get(f"/podcasts/{episode['id']}/chunks").json()[0]
    assert segment["episode_language"] == "en"
    assert segment["transcript"]["text"] == "Hello"
    assert client.get(f"/podcasts/chunks/{segment['id']}").json()["episode_language"] == "en"
    assert client.post("/podcasts", json={**payload, "language": "ja"}).status_code == 409

    updated = client.patch(f"/podcasts/{episode['id']}", json={"title": "English", "author": "Author", "language": "ja"})
    assert updated.json()["language"] == "ja"
    segment = client.get(f"/podcasts/chunks/{segment['id']}").json()
    assert segment["episode_language"] == "ja"
    assert segment["transcript"]["text"] == "Hello"


def test_podcast_default_and_invalid_language(client):
    payload = {"audio_location": "audio", "title": "Episode", "author": "Author", "chunk_interval": 60,
               "podcast_details": {"provider": "youtube", "id": "video"}}
    assert client.post("/podcasts", json={**payload, "language": "fr"}).status_code == 422
    assert client.post("/podcasts", json=payload).json()["language"] == "ja"


def test_external_transcript_is_used_on_create_instead_of_youtube(client, monkeypatch):
    def fail_if_called(*args):
        raise AssertionError("An uploaded transcript should bypass the transcript provider")
    monkeypatch.setattr("app.api.podcast.get_transcript", fail_if_called)
    payload = {
        "audio_location": "external-audio", "title": "Episode", "author": "Author",
        "chunk_interval": 20, "podcast_details": {"provider": "youtube", "id": "video"},
        "external_transcript": "[00:00] Hello\n[00:20] Next\n[00:41] Last",
    }
    response = client.post("/podcasts", json=payload)
    assert response.status_code == 200
    chunks = client.get(f"/podcasts/{response.json()['id']}/chunks").json()
    assert [chunk["transcript"]["text"] for chunk in chunks] == ["Hello", "Next", "Last"]
    assert client.post("/podcasts", json=payload).status_code == 409


def test_external_transcript_edit_is_atomic_and_optional(client):
    response = client.post("/podcasts", json={
        "audio_location": "edit-external", "title": "Before", "author": "Author",
        "chunk_interval": 20, "podcast_details": {"provider": "spotify", "id": "episode"},
        "external_transcript": "A plain transcript.\nSecond line.",
    })
    episode_id = response.json()["id"]
    def texts():
        return [chunk["transcript"]["text"] for chunk in client.get(f"/podcasts/{episode_id}/chunks").json()]
    assert texts() == ["A plain transcript.\nSecond line.", "", ""]
    update = {"title": "After", "author": "Author", "external_transcript": "[00:05] First\n[00:40] Third"}
    assert client.patch(f"/podcasts/{episode_id}", json=update).status_code == 200
    assert texts() == ["First", "", "Third"]
    assert client.patch(f"/podcasts/{episode_id}", json={"title": "Changed", "author": "Author"}).status_code == 200
    assert texts() == ["First", "", "Third"]
    for invalid in ("", "[00:10] Text\nno timestamp", "[01:00] Outside", "[00:70] Invalid"):
        assert client.patch(f"/podcasts/{episode_id}", json={**update, "external_transcript": invalid}).status_code == 422
        assert texts() == ["First", "", "Third"]
        assert client.get(f"/podcasts/{episode_id}").json()["title"] == "Changed"
    assert client.patch("/podcasts/999999", json=update).status_code == 404


@pytest.mark.parametrize(('file_format', 'contents'), [
    ('srt', '1\n00:00:00,000 --> 00:00:03,000\n<i>First</i> line\ncontinued\n\n2\n00:00:20,000 --> 00:00:22,000\nSecond &amp; next\n\n3\n00:00:40,000 --> 00:00:42,000\nFinal'),
    ('vtt', 'WEBVTT\n\nNOTE Example comment\nignored\n\nfirst-cue\n00:00.000 --> 00:03.000 align:start\n<i>First</i> line\ncontinued\n\n00:20.000 --> 00:22.000\nSecond &amp; next\n\n00:40.000 --> 00:42.000\nFinal'),
])
def test_subtitles_are_assigned_to_segments_on_create_edit_and_resize(client, file_format, contents):
    response = client.post('/podcasts', json={
        'audio_location': f'audio-{file_format}', 'title': 'Episode', 'author': 'Author',
        'chunk_interval': 20, 'podcast_details': {'provider': 'spotify', 'id': 'test'},
        'external_transcript': contents, 'external_transcript_format': file_format,
    })
    assert response.status_code == 200
    episode_id = response.json()['id']

    def texts():
        chunks = client.get(f'/podcasts/{episode_id}/chunks').json()
        return [(chunk['start_time'], chunk['end_time'], chunk['transcript']['text']) for chunk in chunks]

    assert texts() == [(0, 20, 'First line\ncontinued'), (20, 40, 'Second & next'), (40, 60, 'Final')]
    update = {'title': 'Episode', 'author': 'Author', 'external_transcript': contents,
              'external_transcript_format': file_format}
    assert client.patch(f'/podcasts/{episode_id}', json=update).status_code == 200
    assert texts() == [(0, 20, 'First line\ncontinued'), (20, 40, 'Second & next'), (40, 60, 'Final')]
    update['chunk_interval'] = 30
    assert client.patch(f'/podcasts/{episode_id}', json=update).status_code == 200
    assert texts() == [(0, 30, 'First line\ncontinued Second & next'), (30, 60, 'Final')]
    assert client.patch(f'/podcasts/{episode_id}', json={**update, 'chunk_interval': 15}).status_code == 200
    assert texts() == [(0, 15, 'First line\ncontinued'), (15, 30, 'Second & next'), (30, 45, 'Final'), (45, 60, '')]


@pytest.mark.parametrize(('file_format', 'contents'), [
    ('vtt', 'Not WEBVTT\n\n00:00.000 --> 00:01.000\nText'),
    ('vtt', 'WEBVTT\n\n00:00.000 --> 00:00.000\nText'),
    ('srt', '1\n00:00:00,000 --> bad\nText'),
    ('srt', '1\n00:00:60,000 --> 00:01:01,000\nText'),
    ('srt', '1\n00:00:00,000 --> 00:00:01,000\n<i></i>'),
])
def test_invalid_subtitle_upload_does_not_change_episode(client, file_format, contents):
    response = client.post('/podcasts', json={
        'audio_location': 'subtitle-edit', 'title': 'Original', 'author': 'Author',
        'chunk_interval': 20, 'podcast_details': {'provider': 'spotify', 'id': 'test'},
        'external_transcript': '[00:00] Original',
    })
    episode_id = response.json()['id']
    chunks = client.get(f'/podcasts/{episode_id}/chunks').json()
    result = client.patch(f'/podcasts/{episode_id}', json={
        'title': 'Changed', 'author': 'Author', 'chunk_interval': 30,
        'external_transcript': contents, 'external_transcript_format': file_format,
    })
    assert result.status_code == 422
    assert client.get(f'/podcasts/{episode_id}').json()['title'] == 'Original'
    assert client.get(f'/podcasts/{episode_id}/chunks').json() == chunks


def test_vocabulary_ranges_baseline_and_replacement(client, monkeypatch):
    from types import SimpleNamespace
    scores = {"1": 5, "2": 1}
    monkeypatch.setattr("app.services.podcast.vocabulary.ratings", lambda session, user_id, language: dict(scores))
    calls = []
    def parse(session, text, user_id, language):
        calls.append(text)
        return [SimpleNamespace(word_id=int(word), display=True, text=word) if word.isdigit()
                else SimpleNamespace(word_id=None, display=False, text=word) for word in text.split()]
    monkeypatch.setattr("app.services.podcast.vocabulary.parse_groups", parse)
    episode_id = client.post("/podcasts", json={
        "audio_location": "vocab", "title": "Vocabulary", "author": "Author", "chunk_interval": 30,
        "podcast_details": {"provider": "spotify", "id": "id"},
        "external_transcript": "[00:00] 1 1 2 3 unknown\n[00:30] 3 3",
    }).json()["id"]
    scores.update({"2": 3, "3": 4})
    result = client.get(f"/podcasts/{episode_id}/vocabulary").json()
    assert result["baseline_at"]
    assert result["episode"]["baseline"]["familiarity_low"] == 35.0
    assert result["episode"]["baseline"]["familiarity_high"] == 85.0
    assert result["episode"]["current"]["familiarity_low"] == 83.3
    assert result["episode"]["current"]["difficulty_high"] == 16.7
    assert result["episode"]["current"]["unmatched_groups"] == 1
    assert result["episode"]["improved_unique"] == 1
    assert result["episode"]["newly_rated_unique"] == 1
    assert len(result["segments"]) == 2
    assert result["segments_with_text"] == 2
    client.get(f"/podcasts/{episode_id}/vocabulary")
    assert len(calls) == 2
    response = client.patch(f"/podcasts/{episode_id}", json={"title": "Vocabulary", "author": "Author", "external_transcript": "[00:00] 2 3"})
    assert response.status_code == 200
    updated = client.get(f"/podcasts/{episode_id}/vocabulary").json()
    assert updated["episode"]["baseline"] == updated["episode"]["current"]
    assert updated["episode"]["newly_rated_unique"] == 0
    assert updated["segments_with_text"] == 1
    assert len(calls) == 3


def test_vocabulary_empty_and_other_users(client):
    episode_id = client.post("/podcasts", json={"audio_location": "no-text", "title": "No text", "author": "A",
        "chunk_interval": 30, "podcast_details": {"provider": "spotify", "id": "id"}}).json()["id"]
    response = client.get(f"/podcasts/{episode_id}/vocabulary")
    assert response.status_code == 200
    assert response.json()["episode"] is None
    assert response.json()["baseline_at"] is None
    assert client.get("/podcasts/999999/vocabulary").status_code == 404


def test_english_vocabulary_uses_dictionary_and_saved_ratings(client, monkeypatch):
    from app.db.models.english_vocab import EnglishDictionary, EnglishWordFamiliarity
    from app.services.podcast import vocabulary
    from sqlalchemy import select

    def real_ratings(session, user_id, language):
        return {str(word): score for word, score in session.execute(
            select(EnglishWordFamiliarity.word_id, EnglishWordFamiliarity.familiarity_score)
            .where(EnglishWordFamiliarity.user_id == user_id))}
    monkeypatch.setattr(vocabulary, "ratings", real_ratings)
    with next(iter(app.dependency_overrides[get_db]())) as session:
        EnglishDictionary.__table__.create(session.bind)
        EnglishWordFamiliarity.__table__.create(session.bind)
        session.add_all([EnglishDictionary(word_id=1, headword="word", lookup_key="word", meaning="単語"),
                         EnglishDictionary(word_id=2, headword="go", lookup_key="go", meaning="行く")])
        session.add(EnglishWordFamiliarity(user_id=1, word_id=1, familiarity_score=1))
        session.commit()
    episode_id = client.post("/podcasts", json={"audio_location": "english-vocab", "title": "English", "author": "A",
        "language": "en", "chunk_interval": 60, "podcast_details": {"provider": "spotify", "id": "id"},
        "external_transcript": "Words went."}).json()["id"]
    assert client.patch("/eng/update_familiarity_score", json={"word_id": 1, "new_score": 5}).status_code == 200
    result = client.get(f"/podcasts/{episode_id}/vocabulary").json()["episode"]
    assert result["baseline"]["familiarity_low"] == 5
    assert result["baseline"]["familiarity_high"] == 55
    assert result["current"]["familiarity_low"] == 50
    assert result["current"]["familiarity_high"] == 100
    assert result["improved_unique"] == 1


def test_episode_added_date_is_preserved_and_legacy_dates_are_unknown(client):
    from datetime import datetime
    from sqlalchemy import update

    episode = client.post("/podcasts", json={"audio_location": "date-added", "title": "Episode", "author": "A",
        "chunk_interval": 30, "podcast_details": {"provider": "spotify", "id": "id"}}).json()
    episode_id = episode["id"]
    added_at = episode["added_at"]
    assert added_at is not None
    datetime.fromisoformat(added_at.replace("Z", "+00:00"))
    assert client.get(f"/podcasts/{episode_id}").json()["added_at"] == added_at
    assert client.get(f"/podcasts/{episode_id}/vocabulary").json()["added_at"] == added_at
    assert client.patch(f"/podcasts/{episode_id}", json={"title": "Updated", "author": "A"}).json()["added_at"] == added_at

    # Episodes that predate the feature must not be given an invented date.
    with next(iter(app.dependency_overrides[get_db]())) as session:
        session.execute(update(PodcastEpisode).where(PodcastEpisode.id == episode_id).values(added_at=None))
        session.commit()
    assert client.get(f"/podcasts/{episode_id}").json()["added_at"] is None
    assert client.get(f"/podcasts/{episode_id}/vocabulary").json()["added_at"] is None
