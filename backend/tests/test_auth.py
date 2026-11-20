from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models.user import User
from app.db.models.podcast import PodcastEpisode
from app.db.session import get_db
from app.main import app


@pytest.fixture
def auth_setup(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setenv("CLERK_JWT_KEY", public_key)
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "http://localhost:5173")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.__table__.create(engine)
    PodcastEpisode.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as db:
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client:
            yield client, db, private_key
        app.dependency_overrides.clear()
    engine.dispose()


def token(key, sub="user_one", azp="http://localhost:5173", expires=60):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": sub, "azp": azp, "iat": now, "nbf": now, "exp": now + timedelta(seconds=expires)}, key, algorithm="RS256")


def headers(value):
    return {"Authorization": f"Bearer {value}"}


def test_sessions_are_verified_and_users_are_isolated(auth_setup):
    client, db, key = auth_setup
    assert client.get("/api/podcasts").status_code == 401
    assert client.get("/api/podcasts", headers=headers("invalid")).status_code == 401
    assert client.get("/api/podcasts", headers=headers(token(key, expires=-60))).status_code == 401
    assert client.get("/api/podcasts", headers=headers(token(key, azp="https://untrusted.example"))).status_code == 401
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert client.get("/api/podcasts", headers=headers(token(wrong_key))).status_code == 401
    one, two = headers(token(key)), headers(token(key, sub="user_two"))
    assert client.get("/api/podcasts", headers=one).json() == []
    first = db.scalar(select(User).where(User.clerk_id == "user_one"))
    db.add(PodcastEpisode(user_id=first.id, audio_location="https://example.com", title="Private", author="Author", duration=100, language="ja"))
    db.commit()
    episode = db.scalar(select(PodcastEpisode))
    assert len(client.get("/api/podcasts", headers=one).json()) == 1
    assert client.get("/api/podcasts", headers=two).json() == []
    assert client.get(f"/api/podcasts/{episode.id}", headers=two).status_code == 404
    assert client.delete(f"/api/podcasts/{episode.id}", headers=two).status_code == 404
    assert len(db.scalars(select(User)).all()) == 2


def test_missing_configuration_fails_closed(auth_setup, monkeypatch):
    client, _db, key = auth_setup
    monkeypatch.delenv("CLERK_AUTHORIZED_PARTIES")
    assert client.get("/api/podcasts", headers=headers(token(key))).status_code == 503


def test_learning_language_is_saved_per_account(auth_setup):
    client, _db, key = auth_setup
    one, two = headers(token(key)), headers(token(key, sub="user_two"))
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/profile", headers=one).json() == {"learning_language": "ja", "onboarding_required": True, "levels": {"ja": None, "en": None}}
    assert client.put("/api/profile", headers=one, json={"learning_language": "en"}).json() == {"learning_language": "en"}
    assert client.get("/api/profile", headers=one).json() == {"learning_language": "en", "onboarding_required": False, "levels": {"ja": None, "en": None}}
    assert client.get("/api/profile", headers=two).json() == {"learning_language": "ja", "onboarding_required": True, "levels": {"ja": None, "en": None}}
    assert client.put("/api/profile", headers=two, json={"learning_language": "ja"}).status_code == 200
    assert client.get("/api/profile", headers=two).json() == {"learning_language": "ja", "onboarding_required": False, "levels": {"ja": None, "en": None}}
    assert client.put("/api/profile", headers=one, json={"learning_language": "fr"}).status_code == 422
    assert client.get("/api/profile", headers=one).json() == {"learning_language": "en", "onboarding_required": False, "levels": {"ja": None, "en": None}}


def test_profile_levels_are_validated_and_isolated(auth_setup):
    client, _db, key = auth_setup
    one, two = headers(token(key)), headers(token(key, sub="user_two"))
    assert client.put("/api/profile/level", headers=one, json={"language": "ja", "level": "N4"}).status_code == 200
    assert client.put("/api/profile/level", headers=one, json={"language": "en", "level": "A2"}).status_code == 200
    assert client.put("/api/profile/level", headers=one, json={"language": "en", "level": "N4"}).status_code == 422
    assert client.get("/api/profile", headers=one).json()["levels"] == {"ja": "N4", "en": "A2"}
    assert client.get("/api/profile", headers=two).json()["levels"] == {"ja": None, "en": None}
    assert client.put("/api/profile/level", headers=one, json={"language": "ja", "level": None}).status_code == 200
    assert client.get("/api/profile", headers=one).json()["levels"] == {"ja": None, "en": "A2"}
