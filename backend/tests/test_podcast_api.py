import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models.podcast import PodcastChunk, PodcastEpisode, PodcastTranscript
from app.db.models.user import User
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    for model in (User, PodcastEpisode, PodcastChunk, PodcastTranscript):
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
    episode = {"audio_location": "https://example.com/audio", "title": "Episode", "author": "Author", "duration": 60}
    first = client.post('/podcasts', json=episode)
    assert first.status_code == 200
    episode_id = first.json()['id']
    assert client.post('/podcasts', json={**episode, 'title': 'Other'}).json() == first.json()
    assert client.get(f'/podcasts/{episode_id}').json() == first.json()
    assert client.post(f'/podcasts/{episode_id}/chunks', json={'start_time': 10, 'end_time': 61}).status_code == 422
    assert client.post(f'/podcasts/{episode_id}/chunks', json={'start_time': 10, 'end_time': 10}).status_code == 422
    chunk = client.post(f'/podcasts/{episode_id}/chunks', json={'start_time': 10, 'end_time': 20})
    assert chunk.status_code == 201
    chunk_id = chunk.json()['id']
    assert client.put(f'/podcasts/chunks/{chunk_id}/transcript', json={'text': 'first'}).json()['text'] == 'first'
    assert client.put(f'/podcasts/chunks/{chunk_id}/transcript', json={'text': 'updated'}).json()['text'] == 'updated'
    assert client.get(f'/podcasts/{episode_id}/chunks').json()[0]['transcript']['text'] == 'updated'
    assert client.delete(f'/podcasts/chunks/{chunk_id}').status_code == 204
    assert client.get(f'/podcasts/chunks/{chunk_id}').status_code == 404
    assert client.get(f'/podcasts/{episode_id}/chunks').json() == []
    assert client.post('/podcasts/999/chunks', json={'start_time': 0, 'end_time': 1}).status_code == 404


def test_chunks_are_scoped_to_current_user(client):
    episode_id = client.post('/podcasts', json={
        'audio_location': 'audio', 'title': 'Episode', 'author': 'Author', 'duration': 60
    }).json()['id']
    with next(iter(app.dependency_overrides[get_db]())) as session:
        other = PodcastChunk(user_id=2, podcast_id=episode_id, start_time=0, end_time=1)
        session.add(other)
        session.commit()
        other_id = other.id
    assert client.get(f'/podcasts/{episode_id}/chunks').json() == []
    assert client.get(f'/podcasts/chunks/{other_id}').status_code == 404
    assert client.put(f'/podcasts/chunks/{other_id}/transcript', json={'text': 'text'}).status_code == 404
    assert client.delete(f'/podcasts/chunks/{other_id}').status_code == 404
