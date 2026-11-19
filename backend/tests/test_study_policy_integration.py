from app.auth import current_user_id
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from fsrs import Card, State
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import DEVELOPMENT_USER_ID
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseWordFamiliarity
from app.db.models.podcast import PodcastChunk, PodcastEpisode, PodcastTranscript
from app.db.models.study import (StudyCard, StudyMembership, StudyReview, VocabularyOccurrence,
                                 WordStudyFamiliarity, WordStudyReview, WordStudySchedule)
from app.db.models.user import User
from app.db.session import get_db
from app.main import app


@compiles(JSONB, "sqlite")
def _jsonb_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
def study(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    for model in (User, JapaneseDictionary, JapaneseWordFamiliarity, PodcastEpisode, PodcastChunk,
                  PodcastTranscript, StudyCard, StudyReview, WordStudyFamiliarity, StudyMembership, WordStudySchedule,
                  VocabularyOccurrence, WordStudyReview):
        model.__table__.create(engine)
    clock = [datetime(2026, 1, 1, 9, tzinfo=timezone.utc)]
    monkeypatch.setattr("app.api.study.utc_now", lambda: clock[0])
    with Session(engine, expire_on_commit=False) as db:
        db.add(User(id=DEVELOPMENT_USER_ID, name="test"))
        db.add(JapaneseDictionary(word_id=7, source_entry_id=1, senses=[{"glosses": ["cat"]}], jlpt_level="N5"))
        db.flush()
        db.add(PodcastEpisode(id=10, user_id=DEVELOPMENT_USER_ID, audio_location="test", title="Episode", author="Test", duration=100, language="ja"))
        db.flush()
        db.add(PodcastChunk(id=11, user_id=DEVELOPMENT_USER_ID, podcast_id=10, start_time=0, end_time=100))
        db.flush()
        db.add(PodcastTranscript(podcast_chunk_id=11, text="猫です。猫がいます。"))
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                yield client, db, clock
        finally:
            app.dependency_overrides.clear()
    engine.dispose()


def card_payload(second=False):
    if second:
        return {"word_id": 7, "segment_id": 11, "sentence_start": 4, "sentence_end": 10,
                "target_start": 4, "target_end": 5, "reading": "ねこ", "sentence": "猫がいます。", "target_text": "猫"}
    return {"word_id": 7, "segment_id": 11, "sentence_start": 0, "sentence_end": 4,
            "target_start": 0, "target_end": 1, "reading": "ねこ", "sentence": "猫です。", "target_text": "猫"}


def test_settings_persist_and_apply_to_new_and_existing_cards_at_review(study):
    client, db, clock = study
    assert client.get("/api/study/settings").json() == {
        "retention_percent": 90, "maximum_interval": 36500, "fuzzing": True,
        "shortcuts": {"show_answer": "Enter", "again": "a", "hard": "s", "good": "d", "easy": "f"},
    }
    first = client.post("/api/study/cards", json=card_payload()).json()
    schedule = db.get(WordStudySchedule, first["id"])
    state = Card(card_id=first["id"], state=State.Review, step=None, stability=20,
                 difficulty=5, last_review=clock[0] - timedelta(days=20), due=clock[0])
    schedule.serialized_state = state.to_dict()
    schedule.next_review_at = state.due
    schedule.next_eligible_at = state.due
    db.commit()
    settings = {"retention_percent": 95, "maximum_interval": 3, "fuzzing": False}
    expected = {**settings, "shortcuts": {"show_answer": "Enter", "again": "a", "hard": "s", "good": "d", "easy": "f"}}
    assert client.put("/api/study/settings", json=settings).json() == expected
    assert client.get("/api/study/settings").json() == expected
    db.expire_all()
    schedule = db.get(WordStudySchedule, first["id"])
    assert schedule.scheduler_config["desired_retention"] == 0.9
    assert schedule.serialized_state == state.to_dict()
    second = client.post("/api/study/cards", json=card_payload(second=True)).json()
    assert db.get(WordStudySchedule, second["id"]).scheduler_config["desired_retention"] == 0.95
    result = client.post(f"/api/study/cards/{first['id']}/review", json={"rating": 3, "version": first["version"]})
    assert result.status_code == 200
    db.expire_all()
    schedule = db.get(WordStudySchedule, first["id"])
    assert schedule.scheduler_config["desired_retention"] == 0.95
    assert schedule.scheduler_config["maximum_interval"] == 3
    assert schedule.scheduler_config["enable_fuzzing"] is False
    assert datetime.fromisoformat(schedule.serialized_state["due"]) <= clock[0] + timedelta(days=3)


@pytest.mark.parametrize("settings", [
    {"retention_percent": 69, "maximum_interval": 1, "fuzzing": True},
    {"retention_percent": 98, "maximum_interval": 1, "fuzzing": True},
    {"retention_percent": 90, "maximum_interval": 0, "fuzzing": True},
    {"retention_percent": 90, "maximum_interval": 36501, "fuzzing": True},
    {"retention_percent": 90.5, "maximum_interval": 1, "fuzzing": True},
])
def test_invalid_settings_do_not_change_saved_preferences(study, settings):
    client, _, _ = study
    assert client.put("/api/study/settings", json=settings).status_code == 422
    assert client.get("/api/study/settings").json()["retention_percent"] == 90


def test_familiarity_updates_do_not_enroll(study):
    client, db, _ = study
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 4}).status_code == 200
    assert client.post("/api/vocabulary/mark-known", json={"language": "ja", "level": "N5"}).status_code == 200
    assert db.scalars(select(StudyMembership)).all() == []
    assert db.scalars(select(WordStudySchedule)).all() == []
    assert client.get("/api/study/cards?due_only=true").json() == []


def test_stats_count_only_due_enrolled_cards_and_local_daily_completions(study, monkeypatch):
    client, db, clock = study
    first = client.post("/api/study/cards", json=card_payload()).json()
    second = client.post("/api/study/cards", json=card_payload(second=True)).json()
    assert first["is_due"] and second["is_due"]
    # Jan 1 in Singapore begins at Dec 31 16:00 UTC. Repeated reviews of
    # the same card count once; a review outside the local day does not count.
    for card_id, when in [
        (first["id"], datetime(2025, 12, 31, 15, 59, tzinfo=timezone.utc)),
        (first["id"], datetime(2025, 12, 31, 16, 0, tzinfo=timezone.utc)),
        (first["id"], datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)),
        (second["id"], datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)),
    ]:
        db.add(WordStudyReview(card_id=card_id, user_id=DEVELOPMENT_USER_ID, word_id=7,
            rating=3, reviewed_at=when, review_log={}, model_version="test"))
    db.commit()
    response = client.get("/api/study/stats", params={"timezone": "Asia/Singapore"})
    assert response.status_code == 200
    assert response.json() == {"due_count": 2, "due_today_count": 2, "completed_count": 2}
    # The local-day boundary is half-open: 23:59 Singapore time is today,
    # while exactly midnight is tomorrow. Future cards never appear due now.
    schedule = db.get(WordStudySchedule, second["id"])
    schedule.next_eligible_at = datetime(2026, 1, 1, 15, 59, tzinfo=timezone.utc)
    db.commit()
    assert client.get("/api/study/stats", params={"timezone": "Asia/Singapore"}).json() == {
        "due_count": 1, "due_today_count": 2, "completed_count": 2}
    schedule.next_eligible_at = datetime(2026, 1, 1, 16, 0, tzinfo=timezone.utc)
    db.commit()
    assert client.get("/api/study/stats", params={"timezone": "Asia/Singapore"}).json() == {
        "due_count": 1, "due_today_count": 1, "completed_count": 2}
    assert client.delete(f"/api/study/cards/{first['id']}").status_code == 204
    assert client.get("/api/study/stats", params={"timezone": "Asia/Singapore"}).json() == {"due_count": 0, "due_today_count": 0, "completed_count": 2}
    assert client.get("/api/study/stats", params={"timezone": "Invalid/Time_Zone"}).status_code == 422

    # Results must be scoped to the resolved user, including review history.
    db.add(User(id=2, name="other"))
    db.commit()
    monkeypatch.setitem(app.dependency_overrides, current_user_id, lambda: 2)
    assert client.get("/api/study/stats").json() == {"due_count": 0, "due_today_count": 0, "completed_count": 0}


def test_due_metadata_tracks_mastery_and_eligibility(study):
    client, _db, _clock = study
    card = client.post("/api/study/cards", json=card_payload()).json()
    assert card["is_due"] and card["review_status"] == "normal"
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 5}).status_code == 200
    mastered = client.get("/api/study/cards").json()[0]
    assert mastered["familiarity_level"] == 5
    assert mastered["review_status"] == "mastered" and not mastered["is_due"]
    assert mastered["next_eligible_at"] is None
    assert client.get("/api/study/stats").json()["due_count"] == 0
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 2}).status_code == 200
    reactivated = client.get("/api/study/cards").json()[0]
    assert reactivated["familiarity_level"] == 2 and reactivated["is_due"]


def test_due_today_uses_local_midnight_across_daylight_saving(study):
    client, db, clock = study
    clock[0] = datetime(2026, 3, 8, 16, tzinfo=timezone.utc)
    card = client.post("/api/study/cards", json=card_payload()).json()
    schedule = db.get(WordStudySchedule, card["id"])
    # New York jumps to daylight saving time on March 8; that day's next
    # midnight is 04:00 UTC, not 05:00 UTC.
    schedule.next_eligible_at = datetime(2026, 3, 9, 3, 59, tzinfo=timezone.utc)
    db.commit()
    stats = client.get("/api/study/stats", params={"timezone": "America/New_York"}).json()
    assert stats["due_count"] == 0 and stats["due_today_count"] == 1
    schedule.next_eligible_at = datetime(2026, 3, 9, 4, 0, tzinfo=timezone.utc)
    db.commit()
    stats = client.get("/api/study/stats", params={"timezone": "America/New_York"}).json()
    assert stats["due_today_count"] == 0


def test_same_word_multiple_sentences_have_independent_schedules(study):
    client, db, _ = study
    first = client.post("/api/study/cards", json=card_payload())
    second = client.post("/api/study/cards", json=card_payload(second=True))
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    assert len(db.scalars(select(StudyMembership)).all()) == 2
    assert len(db.scalars(select(WordStudySchedule)).all()) == 2
    assert len(db.scalars(select(VocabularyOccurrence)).all()) == 2
    assert len(client.get("/api/study/cards?due_only=true").json()) == 2


def test_review_and_removal_of_one_sentence_leave_other_sentence_due(study):
    client, db, _ = study
    first = client.post("/api/study/cards", json=card_payload()).json()
    second = client.post("/api/study/cards", json=card_payload(second=True)).json()
    sibling_state = db.get(WordStudySchedule, second["id"]).serialized_state
    reviewed = client.post(f"/api/study/cards/{first['id']}/review", json={"rating": 3, "version": first["version"]})
    assert reviewed.status_code == 200
    db.expire_all()
    assert db.get(WordStudySchedule, second["id"]).serialized_state == sibling_state
    assert [card["id"] for card in client.get("/api/study/cards?due_only=true").json()] == [second["id"]]
    assert client.delete(f"/api/study/cards/{first['id']}").status_code == 204
    db.expire_all()
    assert not db.get(StudyMembership, first["id"]).active
    assert db.get(StudyMembership, second["id"]).active
    assert [card["id"] for card in client.get("/api/study/cards?due_only=true").json()] == [second["id"]]
    assert [log.card_id for log in db.scalars(select(WordStudyReview)).all()] == [first["id"]]


def test_removal_and_readdition_preserve_review_history_and_state(study):
    client, db, clock = study
    first = client.post("/api/study/cards", json=card_payload()).json()
    result = client.post(f"/api/study/cards/{first['id']}/review", json={"rating": 3, "version": first["version"]})
    assert result.status_code == 200
    reviewed = result.json()
    db.expire_all()
    schedule = db.get(WordStudySchedule, first["id"])
    state, version = schedule.serialized_state, schedule.version
    assert len(db.scalars(select(WordStudyReview)).all()) == 1

    assert client.delete(f"/api/study/cards/{first['id']}").status_code == 204
    db.expire_all()
    assert not db.get(StudyMembership, first["id"]).active
    assert client.get("/api/study/cards?due_only=true").json() == []
    assert len(db.scalars(select(WordStudyReview)).all()) == 1
    assert len(db.scalars(select(VocabularyOccurrence)).all()) == 1

    clock[0] += timedelta(days=1)
    readded = client.post("/api/study/cards", json=card_payload())
    assert readded.status_code == 200
    db.expire_all()
    assert readded.json()["id"] == first["id"]
    assert db.get(StudyMembership, first["id"]).active
    schedule = db.get(WordStudySchedule, first["id"])
    assert schedule.serialized_state == state and reviewed["version"] == version
    assert schedule.version > version
    assert len(db.scalars(select(WordStudyReview)).all()) == 1


def test_mastered_and_wont_learn_suspend_without_losing_enrollment(study):
    client, db, _ = study
    card = client.post("/api/study/cards", json=card_payload()).json()
    sibling = client.post("/api/study/cards", json=card_payload(second=True)).json()
    for level in (5, -1):
        assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": level}).status_code == 200
        assert client.get("/api/study/cards?due_only=true").json() == []
        assert client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 3, "version": card["version"]}).status_code == 409
        db.expire_all()
        assert db.get(StudyMembership, card["id"]).active
        assert db.get(StudyMembership, sibling["id"]).active
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 1}).status_code == 200
    assert len(client.get("/api/study/cards?due_only=true").json()) == 2


def test_explicit_add_clears_wont_learn_and_reactivates_other_sentence(study):
    client, db, _ = study
    first = client.post("/api/study/cards", json=card_payload()).json()
    second = client.post("/api/study/cards", json=card_payload(second=True)).json()
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": -1}).status_code == 200
    assert client.get("/api/study/cards?due_only=true").json() == []
    readded = client.post("/api/study/cards", json=card_payload())
    assert readded.status_code == 200 and readded.json()["id"] == first["id"]
    db.expire_all()
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)) is None
    assert {card["id"] for card in client.get("/api/study/cards?due_only=true").json()} == {first["id"], second["id"]}


def test_manual_familiarity_override_and_stale_review_are_respected(study):
    client, db, _ = study
    card = client.post("/api/study/cards", json=card_payload()).json()
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 4}).status_code == 200
    assert client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 3, "version": card["version"]}).status_code == 409
    current = client.get("/api/study/cards").json()[0]
    response = client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 3, "version": current["version"]})
    assert response.status_code == 200
    assert client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 3, "version": current["version"]}).status_code == 409
    db.expire_all()
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)).familiarity_score == 4
    assert len(db.scalars(select(WordStudyReview)).all()) == 1


def test_user_cannot_read_or_modify_another_users_study_card(study, monkeypatch):
    client, db, _ = study
    db.add(User(id=2, name="other"))
    db.commit()
    card = client.post("/api/study/cards", json=card_payload()).json()
    monkeypatch.setitem(app.dependency_overrides, current_user_id, lambda: 2)
    assert client.get("/api/study/cards").json() == []
    assert client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 3, "version": card["version"]}).status_code == 404
    assert client.delete(f"/api/study/cards/{card['id']}").status_code == 404
    db.expire_all()
    assert db.get(StudyMembership, card["id"]).active
    assert len(db.scalars(select(WordStudyReview)).all()) == 0


@pytest.mark.parametrize("level", [3, 4])
def test_review_phase_due_query_uses_actual_recall_probability(study, level):
    client, db, clock = study
    original = client.post("/api/study/cards", json=card_payload()).json()
    first_review = clock[0]
    card = Card(card_id=original["id"], state=State.Review, step=None,
                stability=10.0, difficulty=5.0, last_review=first_review,
                due=first_review + timedelta(days=10))
    schedule = db.get(WordStudySchedule, original["id"])
    schedule.serialized_state = card.to_dict()
    schedule.next_review_at = card.due
    db.commit()
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": level}).status_code == 200
    clock[0] = first_review + timedelta(days=10)
    assert client.get("/api/study/cards?due_only=true").json() == []
    clock[0] = first_review + timedelta(days=40)
    assert len(client.get("/api/study/cards?due_only=true").json()) == 1


def test_unreviewed_familiar_word_still_requires_first_review(study):
    client, _db, _clock = study
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 4}).status_code == 200
    card = client.post("/api/study/cards", json=card_payload()).json()
    assert len(client.get("/api/study/cards?due_only=true").json()) == 1
    assert client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 3, "version": card["version"]}).status_code == 200


def test_success_and_lapse_update_familiarity_with_review_history(study):
    client, db, clock = study
    card = client.post("/api/study/cards", json=card_payload()).json()
    good = client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 3, "version": card["version"]})
    assert good.status_code == 200
    db.expire_all()
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)).familiarity_score == 2
    updated = good.json()
    clock[0] = datetime.fromisoformat(updated["next_eligible_at"].replace("Z", "+00:00"))
    again = client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 1, "version": updated["version"]})
    assert again.status_code == 200
    db.expire_all()
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)).familiarity_score == 1
    logs = db.scalars(select(WordStudyReview).order_by(WordStudyReview.id)).all()
    assert [log.rating for log in logs] == [3, 1]
    assert again.json()["state"] in ("learning", "relearning")


def test_manual_choice_is_retained_while_review_demotes_effective_level(study):
    client, db, _ = study
    card = client.post("/api/study/cards", json=card_payload()).json()
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 3}).status_code == 200
    current = client.get("/api/study/cards").json()[0]
    result = client.post(f"/api/study/cards/{card['id']}/review", json={"rating": 1, "version": current["version"]})
    assert result.status_code == 200
    db.expire_all()
    familiarity = db.get(WordStudyFamiliarity, (DEVELOPMENT_USER_ID, 7))
    assert familiarity.manual_level == 3
    assert familiarity.policy_level == 2
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)).familiarity_score == 2


def test_distinct_review_dates_and_stability_control_automatic_promotion(study):
    client, db, clock = study
    card_response = client.post("/api/study/cards", json=card_payload()).json()
    second = client.post("/api/study/cards", json=card_payload(second=True)).json()
    first_day = clock[0]
    simulated = Card(card_id=card_response["id"], state=State.Review, step=None, stability=10.0,
                     difficulty=5.0, last_review=first_day - timedelta(days=10), due=first_day)
    schedule = db.get(WordStudySchedule, card_response["id"])
    schedule.serialized_state = simulated.to_dict()
    schedule.next_review_at = simulated.due
    for hour in (1, 2):
        db.add(WordStudyReview(card_id=second["id"], user_id=DEVELOPMENT_USER_ID, word_id=7, rating=3,
            reviewed_at=first_day - timedelta(days=2, hours=hour), review_log={}, model_version=schedule.model_version))
    db.commit()
    assert client.delete(f"/api/study/cards/{second['id']}").status_code == 204
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 2}).status_code == 200
    current = client.get("/api/study/cards").json()[0]
    first = client.post(f"/api/study/cards/{card_response['id']}/review", json={"rating": 3, "version": current["version"]})
    assert first.status_code == 200
    db.expire_all()
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)).familiarity_score == 2
    first_result = first.json()
    clock[0] = datetime.fromisoformat(first_result["next_eligible_at"].replace("Z", "+00:00"))
    assert clock[0].date() > first_day.date()
    later = client.post(f"/api/study/cards/{card_response['id']}/review", json={"rating": 2, "version": first_result["version"]})
    assert later.status_code == 200
    db.expire_all()
    familiarity = db.get(WordStudyFamiliarity, (DEVELOPMENT_USER_ID, 7))
    assert familiarity.policy_level == 3 and familiarity.manual_level == 2
    assert db.get(JapaneseWordFamiliarity, (DEVELOPMENT_USER_ID, 7)).familiarity_score == 3


def test_automatic_promotion_recomputes_sibling_due_without_changing_its_memory(study):
    client, db, clock = study
    first = client.post("/api/study/cards", json=card_payload()).json()
    second = client.post("/api/study/cards", json=card_payload(second=True)).json()
    now = clock[0]
    for item, elapsed in ((first, 10), (second, 20)):
        state = Card(card_id=item["id"], state=State.Review, step=None, stability=10.0,
                     difficulty=5.0, last_review=now - timedelta(days=elapsed),
                     due=now - timedelta(days=elapsed - 10))
        schedule = db.get(WordStudySchedule, item["id"])
        schedule.serialized_state = state.to_dict()
        schedule.next_review_at = state.due
    second_state = db.get(WordStudySchedule, second["id"]).serialized_state
    for days in (2, 4):
        db.add(WordStudyReview(card_id=second["id"], user_id=DEVELOPMENT_USER_ID, word_id=7,
            rating=3, reviewed_at=now - timedelta(days=days), review_log={},
            model_version=db.get(WordStudySchedule, second["id"]).model_version))
    db.commit()
    assert client.patch("/api/jap/update_familiarity_score", json={"word_id": 7, "new_score": 2}).status_code == 200
    cards = {card["id"]: card for card in client.get("/api/study/cards?due_only=true").json()}
    assert set(cards) == {first["id"], second["id"]}
    result = client.post(f"/api/study/cards/{first['id']}/review", json={"rating": 3, "version": cards[first["id"]]["version"]})
    assert result.status_code == 200
    db.expire_all()
    assert db.get(WordStudyFamiliarity, (DEVELOPMENT_USER_ID, 7)).policy_level == 3
    assert db.get(WordStudySchedule, second["id"]).serialized_state == second_state
    assert second["id"] not in {card["id"] for card in client.get("/api/study/cards?due_only=true").json()}


def test_custom_shortcuts_persist_and_reject_conflicts(study):
    client, _, _ = study
    settings = {"retention_percent": 90, "maximum_interval": 36500, "fuzzing": True,
                "shortcuts": {"show_answer": "Space", "again": "1", "hard": "2", "good": "3", "easy": "ArrowRight"}}
    assert client.put("/api/study/settings", json=settings).json() == settings
    assert client.get("/api/study/settings").json() == settings
    duplicate = {**settings, "shortcuts": {**settings["shortcuts"], "easy": "space"}}
    assert client.put("/api/study/settings", json=duplicate).status_code == 422
    invalid = {**settings, "shortcuts": {**settings["shortcuts"], "easy": "Ctrl+X"}}
    assert client.put("/api/study/settings", json=invalid).status_code == 422
    assert client.get("/api/study/settings").json() == settings
    # Old clients that save scheduling preferences do not erase custom keys.
    legacy = {key: settings[key] for key in ("retention_percent", "maximum_interval", "fuzzing")}
    assert client.put("/api/study/settings", json=legacy).json() == settings
