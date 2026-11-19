"""Explicit vocabulary enrollment and FSRS reviews."""
import hashlib
import json
from datetime import datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fsrs import Card, Rating, Scheduler, State
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import current_user_id
from app.data_access.podcast import get_chunk
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseWordFamiliarity
from app.db.models.english_vocab import EnglishDictionary, EnglishWordFamiliarity
from app.db.models.english_study import EnglishStudyCard, EnglishStudyMembership, EnglishStudyOccurrence, EnglishStudyFamiliarity, EnglishStudyReview, EnglishStudySchedule
from app.services.english_vocab import _dictionary_senses
from app.db.models.study import StudyCard, StudyMembership, VocabularyOccurrence, WordStudyFamiliarity, WordStudyReview, WordStudySchedule
from app.db.models.user import User
from app.db.session import get_db
from app.services.study_membership import lock_word_study, refresh_manual_familiarity, sync_word_schedules
from app.services.study_policy import eligibility, policy_after_review
from app.services.podcast.study_context import cue_time, sources_for_word

router = APIRouter(prefix="/study", tags=["study"])
SCHEDULER_VERSION = "py-fsrs-6.3.3/fsrs-6"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AddCardRequest(BaseModel):
    word_id: int = Field(gt=0)
    segment_id: int = Field(gt=0)
    sentence_start: int = Field(ge=0)
    sentence_end: int = Field(gt=0)
    target_start: int = Field(ge=0)
    target_end: int = Field(gt=0)
    reading: str = Field(default="", max_length=500)
    sentence: str = Field(min_length=1)
    target_text: str = Field(min_length=1)
    dictionary_form: str | None = Field(default=None, max_length=500)


class UpdateCardRequest(BaseModel):
    version: int = Field(ge=0)
    reading: str = Field(max_length=500)
    definitions: list[str] = Field(max_length=100)
    sentence: str = Field(min_length=1, max_length=10000)


class CardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    word_id: int
    language: Literal["ja", "en"] = "ja"
    sentence: str
    target_text: str
    dictionary_form: str | None
    reading: str
    definitions: list[str]
    segment_id: int | None
    episode_id: int | None
    episode_title: str | None
    sentence_start: int
    sentence_end: int
    target_start: int
    target_end: int
    due_at: datetime
    created_at: datetime
    version: int
    state: str
    review_status: str
    next_eligible_at: datetime | None
    familiarity_level: int | None
    level_source: str | None
    manual_level: int | None
    is_due: bool
    membership_active: bool


class StudyStatsResponse(BaseModel):
    due_count: int
    due_today_count: int
    completed_count: int


class ReviewRequest(BaseModel):
    rating: Literal[1, 2, 3, 4]
    version: int = Field(ge=0)


DEFAULT_SHORTCUTS = {"show_answer": "Enter", "again": "a", "hard": "s", "good": "d", "easy": "f"}
SPECIAL_SHORTCUTS = {key.lower(): key for key in ("Enter", "Space", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown")}


class StudyShortcuts(BaseModel):
    show_answer: str
    again: str
    hard: str
    good: str
    easy: str

    @field_validator("show_answer", "again", "hard", "good", "easy")
    @classmethod
    def validate_key(cls, value: str) -> str:
        key = value.lower()
        if key in SPECIAL_SHORTCUTS:
            return SPECIAL_SHORTCUTS[key]
        if len(key) == 1 and key in "abcdefghijklmnopqrstuvwxyz0123456789":
            return key
        raise ValueError("Use a letter, number, Enter, Space, or an arrow key")

    @model_validator(mode="after")
    def unique_keys(self):
        if len(set(self.model_dump().values())) != 5:
            raise ValueError("Each review action needs a different key")
        return self


class StudySettings(BaseModel):
    retention_percent: int = Field(ge=70, le=97, strict=True)
    maximum_interval: int = Field(ge=1, le=36500, strict=True)
    fuzzing: bool = Field(strict=True)
    # Older clients can save scheduler settings without resetting shortcuts.
    shortcuts: StudyShortcuts | None = None


def _user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _settings(user: User) -> StudySettings:
    return StudySettings(retention_percent=user.fsrs_retention_percent,
                         maximum_interval=user.fsrs_maximum_interval, fuzzing=user.fsrs_fuzzing,
                         shortcuts=user.study_shortcuts or DEFAULT_SHORTCUTS)


def _apply_settings(scheduler: Scheduler, user: User) -> Scheduler:
    scheduler.desired_retention = user.fsrs_retention_percent / 100
    scheduler.maximum_interval = user.fsrs_maximum_interval
    scheduler.enable_fuzzing = user.fsrs_fuzzing
    return scheduler


@router.get("/settings", response_model=StudySettings)
def get_settings(db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    return _settings(_user(db, user_id))


@router.put("/settings", response_model=StudySettings)
def update_settings(settings: StudySettings, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = _user(db, user_id)
    user.fsrs_retention_percent = settings.retention_percent
    user.fsrs_maximum_interval = settings.maximum_interval
    user.fsrs_fuzzing = settings.fuzzing
    if settings.shortcuts is not None:
        user.study_shortcuts = settings.shortcuts.model_dump()
    db.commit()
    return _settings(user)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def card_response(card: StudyCard, familiarity: WordStudyFamiliarity, schedule: WordStudySchedule, *, active: bool = True) -> dict:
    result = {name: getattr(card, name) for name in (
        "id", "word_id", "sentence", "target_text", "dictionary_form", "reading", "definitions", "segment_id", "episode_id",
        "episode_title", "sentence_start", "sentence_end", "target_start", "target_end")}
    return {**result, "language": "en" if isinstance(card, EnglishStudyCard) else "ja", "due_at": _utc(schedule.next_eligible_at or schedule.next_review_at),
            "created_at": _utc(card.created_at), "version": schedule.version,
            "state": State(schedule.serialized_state["state"]).name.lower(),
            "review_status": schedule.review_status,
            "next_eligible_at": _utc(schedule.next_eligible_at) if schedule.next_eligible_at else None,
            "familiarity_level": familiarity.policy_level, "level_source": familiarity.level_source,
            "manual_level": familiarity.manual_level,
            "membership_active": active,
            "is_due": active and schedule.review_status in ("normal", "deferred") and schedule.next_eligible_at is not None
            and _utc(schedule.next_eligible_at) <= utc_now()}


def _owned_card(db: Session, card_id: int, user_id: int, language: str = "ja") -> StudyCard | EnglishStudyCard:
    StudyCard = _models(language)[0]
    card = db.scalar(select(StudyCard).where(StudyCard.id == card_id, StudyCard.user_id == user_id))
    if card is None:
        raise HTTPException(status_code=404, detail="Study card not found")
    return card


def _schedule(db: Session, card_id: int, language: str = "ja") -> WordStudySchedule | EnglishStudySchedule:
    WordStudySchedule = _models(language)[4]
    result = db.get(WordStudySchedule, card_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Study schedule not found")
    return result


def _enroll(db: Session, card: StudyCard | EnglishStudyCard, now: datetime, user_id: int):
    language = "en" if isinstance(card, EnglishStudyCard) else "ja"
    WordStudyFamiliarity, WordStudySchedule, StudyMembership = _models(language)[3], _models(language)[4], _models(language)[1]
    progress_model = EnglishWordFamiliarity if language == "en" else JapaneseWordFamiliarity
    familiarity = lock_word_study(db, user_id, card.word_id, language)
    progress = db.get(progress_model, (user_id, card.word_id))
    cleared_wont_learn = progress is not None and progress.familiarity_score == -1
    if cleared_wont_learn:
        db.delete(progress)
        progress = None
    score = progress.familiarity_score if progress is not None else None
    if familiarity is None:
        familiarity = WordStudyFamiliarity(user_id=user_id, word_id=card.word_id,
            policy_level=score, manual_level=score, level_source="manual" if score is not None else None)
        db.add(familiarity)
        db.flush()
    elif cleared_wont_learn:
        refresh_manual_familiarity(db, familiarity, 0)
    membership = db.get(StudyMembership, card.id)
    if membership is None:
        membership = StudyMembership(card_id=card.id, user_id=user_id, word_id=card.word_id,
            active=True, added_at=now, removed_at=None)
        db.add(membership)
        db.flush()
        scheduler = _apply_settings(Scheduler(), _user(db, user_id))
        state = Card(card_id=card.id, due=now)
        decision = eligibility(state, scheduler, score)
        schedule = WordStudySchedule(card_id=card.id, user_id=user_id, word_id=card.word_id,
            serialized_state=state.to_dict(), scheduler_config=scheduler.to_dict(), model_version=SCHEDULER_VERSION,
            next_review_at=state.due, review_status=decision.status, next_eligible_at=decision.next_eligible_at, version=0)
        db.add(schedule)
        db.flush()
    else:
        schedule = _schedule(db, card.id, language)
        if not membership.active:
            membership.active = True
            membership.removed_at = None
            membership.added_at = now
            schedule.version += 1
    return familiarity, schedule


def _models(language: str):
    if language == "en":
        return EnglishStudyCard, EnglishStudyMembership, EnglishStudyOccurrence, EnglishStudyFamiliarity, EnglishStudySchedule, EnglishStudyReview
    return StudyCard, StudyMembership, VocabularyOccurrence, WordStudyFamiliarity, WordStudySchedule, WordStudyReview


@router.post("/cards", response_model=CardResponse)
def add_card(request: AddCardRequest, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    chunk = get_chunk(db, user_id, request.segment_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    language = chunk.episode.language
    if language not in ("ja", "en"):
        raise HTTPException(status_code=422, detail="Unsupported transcript language")
    StudyCard, StudyMembership, VocabularyOccurrence, WordStudyFamiliarity, WordStudySchedule, WordStudyReview = _models(language)
    text = chunk.transcript.text if chunk.transcript else ""
    if not (request.sentence_start <= request.target_start < request.target_end <= request.sentence_end <= len(text)):
        raise HTTPException(status_code=422, detail="The selected sentence and word do not match the transcript")
    sentence, target = text[request.sentence_start:request.sentence_end], text[request.target_start:request.target_end]
    if sentence != request.sentence or target != request.target_text:
        raise HTTPException(status_code=409, detail="The transcript has changed. Reload it before adding this sentence.")
    if not sentence.strip() or not target.strip():
        raise HTTPException(status_code=422, detail="A sentence and target word are required")
    entry = db.get(EnglishDictionary if language == "en" else JapaneseDictionary, request.word_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Word not found")
    senses = _dictionary_senses(entry.meaning) if language == "en" else entry.senses
    occurrence = json.dumps([request.segment_id, request.word_id, request.sentence_start, request.sentence_end, sentence], ensure_ascii=False)
    key = hashlib.sha256(occurrence.encode("utf-8")).hexdigest()
    now = utc_now()
    existing = db.scalar(select(StudyCard).where(StudyCard.user_id == user_id, StudyCard.occurrence_key == key))
    try:
        if existing is None:
            card = StudyCard(user_id=user_id, word_id=request.word_id, occurrence_key=key,
                episode_id=chunk.podcast_id, segment_id=chunk.id, episode_title=chunk.episode.title,
                sentence=sentence, target_text=target, dictionary_form=request.dictionary_form, reading=request.reading,
                definitions=["; ".join(sense.get("glosses", [])) for sense in senses if sense.get("glosses")],
                sentence_start=request.sentence_start, sentence_end=request.sentence_end,
                target_start=request.target_start, target_end=request.target_end, created_at=now, due_at=now,
                fsrs_card={}, scheduler_version=SCHEDULER_VERSION, scheduler_config=Scheduler().to_dict(), version=0)
            db.add(card)
            db.flush()
            # Legacy data is retained as an occurrence/archive, not used as the canonical schedule.
            card.fsrs_card = Card(card_id=card.id, due=now).to_dict()
            start_ms, end_ms = cue_time(chunk.transcript.cues, request.sentence_start, request.sentence_end)
            db.add(VocabularyOccurrence(card_id=card.id, user_id=user_id, word_id=card.word_id,
                episode_id=chunk.podcast_id, episode_owner_id=user_id,
                segment_id=chunk.id, segment_episode_id=chunk.podcast_id, segment_owner_id=user_id,
                sentence=sentence, surface_form=target, start_ms=start_ms, end_ms=end_ms,
                episode_title=chunk.episode.title, legacy_card_id=card.id))
        else:
            card = existing
            if card.dictionary_form is None and request.dictionary_form:
                card.dictionary_form = request.dictionary_form
        familiarity, schedule = _enroll(db, card, now, user_id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This study card changed concurrently. Please retry.")
    return card_response(card, familiarity, schedule)


@router.get("/cards", response_model=list[CardResponse])
def list_cards(due_only: bool = False, segment_id: int | None = None, include_removed: bool = False, language: Literal["ja", "en"] = "ja", db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    StudyCard, StudyMembership, VocabularyOccurrence, WordStudyFamiliarity, WordStudySchedule, WordStudyReview = _models(language)
    stmt = (select(StudyCard, WordStudyFamiliarity, WordStudySchedule, StudyMembership)
        .join(StudyMembership, StudyMembership.card_id == StudyCard.id)
        .join(WordStudySchedule, WordStudySchedule.card_id == StudyCard.id)
        .join(WordStudyFamiliarity, (WordStudyFamiliarity.user_id == StudyCard.user_id) & (WordStudyFamiliarity.word_id == StudyCard.word_id))
        .where(StudyCard.user_id == user_id))
    if due_only or not include_removed:
        stmt = stmt.where(StudyMembership.active.is_(True))
    if due_only:
        stmt = stmt.where(WordStudySchedule.review_status.in_(["normal", "deferred"]),
                          WordStudySchedule.next_eligible_at.is_not(None), WordStudySchedule.next_eligible_at <= utc_now())
    if segment_id is not None:
        stmt = stmt.where(StudyCard.segment_id == segment_id)
    rows = db.execute(stmt.order_by(WordStudySchedule.next_eligible_at, StudyCard.id)).all()
    return [card_response(card, familiarity, schedule, active=membership.active) for card, familiarity, schedule, membership in rows]


@router.patch("/cards/{card_id}", response_model=CardResponse)
def update_card(card_id: int, request: UpdateCardRequest, language: Literal["ja", "en"] = "ja", db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    StudyCard, StudyMembership, VocabularyOccurrence, WordStudyFamiliarity, WordStudySchedule, WordStudyReview = _models(language)
    card = _owned_card(db, card_id, user_id, language)
    familiarity = lock_word_study(db, user_id, card.word_id, language)
    membership = db.get(StudyMembership, card.id)
    if familiarity is None or membership is None:
        raise HTTPException(status_code=404, detail="Study membership not found")
    if not request.sentence.strip() or any(not item.strip() for item in request.definitions):
        raise HTTPException(status_code=422, detail="Sentence and definitions cannot be blank")
    result = db.execute(update(WordStudySchedule).where(
        WordStudySchedule.card_id == card.id, WordStudySchedule.user_id == user_id,
        WordStudySchedule.version == request.version,
    ).values(version=request.version + 1))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="This card has already changed. Reload it before editing.")
    card.reading = request.reading.strip()
    card.definitions = [item.strip() for item in request.definitions]
    card.sentence = request.sentence.strip()
    db.commit()
    schedule = _schedule(db, card.id, language)
    db.refresh(schedule)
    return card_response(card, familiarity, schedule, active=membership.active)


@router.get("/cards/{card_id}/sources")
def read_card_sources(card_id: int, language: Literal["ja", "en"] = "ja", db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    card = _owned_card(db, card_id, user_id, language)
    models = _models(language)
    return sources_for_word(db, user_id, card.word_id, card_model=models[0], occurrence_model=models[2])


@router.get("/stats", response_model=StudyStatsResponse)
def study_stats(timezone_name: str = Query(default="UTC", alias="timezone", min_length=1, max_length=100),
                language: Literal["ja", "en"] = "ja", db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    """Count currently due cards and distinct cards reviewed on the user's local day."""
    StudyCard, StudyMembership, VocabularyOccurrence, WordStudyFamiliarity, WordStudySchedule, WordStudyReview = _models(language)
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail="Invalid time zone") from None
    now = utc_now()
    local_day = now.astimezone(zone).date()
    start = datetime.combine(local_day, time.min, tzinfo=zone).astimezone(timezone.utc)
    end = datetime.combine(local_day + timedelta(days=1), time.min, tzinfo=zone).astimezone(timezone.utc)
    due_query = select(func.count()).select_from(WordStudySchedule).join(
        StudyMembership, StudyMembership.card_id == WordStudySchedule.card_id
    ).where(
        WordStudySchedule.user_id == user_id,
        StudyMembership.user_id == user_id,
        StudyMembership.active.is_(True),
        WordStudySchedule.review_status.in_(["normal", "deferred"]),
        WordStudySchedule.next_eligible_at.is_not(None),
    )
    due = db.scalar(due_query.where(WordStudySchedule.next_eligible_at <= now))
    due_today = db.scalar(due_query.where(WordStudySchedule.next_eligible_at < end))
    completed = db.scalar(select(func.count(func.distinct(WordStudyReview.card_id))).where(
        WordStudyReview.user_id == user_id,
        WordStudyReview.reviewed_at >= start,
        WordStudyReview.reviewed_at < end,
        WordStudyReview.reviewed_at <= now,
    ))
    return StudyStatsResponse(due_count=due or 0, due_today_count=due_today or 0, completed_count=completed or 0)


@router.post("/cards/{card_id}/review", response_model=CardResponse)
def review_card(card_id: int, request: ReviewRequest, language: Literal["ja", "en"] = "ja", db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    StudyCard, StudyMembership, VocabularyOccurrence, WordStudyFamiliarity, WordStudySchedule, WordStudyReview = _models(language)
    progress_model = EnglishWordFamiliarity if language == "en" else JapaneseWordFamiliarity
    card = _owned_card(db, card_id, user_id, language)
    familiarity = lock_word_study(db, user_id, card.word_id, language)
    membership = db.get(StudyMembership, card.id)
    if familiarity is None or membership is None or not membership.active:
        raise HTTPException(status_code=404, detail="Study membership not active")
    schedule = _schedule(db, card.id, language)
    if schedule.version != request.version:
        raise HTTPException(status_code=409, detail="This card has already changed. Reload it before reviewing.")
    if schedule.model_version != SCHEDULER_VERSION:
        raise HTTPException(status_code=409, detail="This card requires a scheduler migration before review")
    now = utc_now()
    if schedule.next_eligible_at is None or _utc(schedule.next_eligible_at) > now:
        raise HTTPException(status_code=409, detail="This card is not due for review")
    before = schedule.serialized_state
    scheduler = _apply_settings(Scheduler.from_dict(schedule.scheduler_config), _user(db, user_id))
    updated, log = scheduler.review_card(Card.from_dict(before), Rating(request.rating), review_datetime=now)
    after = updated.to_dict()
    dates = {_utc(item).date() for item in db.scalars(select(WordStudyReview.reviewed_at).where(
        WordStudyReview.user_id == user_id, WordStudyReview.word_id == card.word_id,
        WordStudyReview.rating.in_([2, 3, 4]))).all()}
    if request.rating != Rating.Again:
        dates.add(now.date())
    level = policy_after_review(familiarity.policy_level, request.rating, dates, updated.stability)
    if level != (familiarity.policy_level or 1):
        familiarity.policy_level = level
        familiarity.level_source = "auto"
        progress = db.get(progress_model, (user_id, card.word_id))
        if progress is None:
            db.add(progress_model(user_id=user_id, word_id=card.word_id, familiarity_score=level))
        else:
            progress.familiarity_score = level
        sync_word_schedules(db, user_id, card.word_id, level, exclude_card_id=card.id, language=language)
    decision = eligibility(updated, scheduler, familiarity.policy_level)
    result = db.execute(update(WordStudySchedule).where(
        WordStudySchedule.card_id == card.id, WordStudySchedule.user_id == user_id,
        WordStudySchedule.version == request.version,
    ).values(serialized_state=after, scheduler_config=scheduler.to_dict(), next_review_at=updated.due, review_status=decision.status,
             next_eligible_at=decision.next_eligible_at, version=request.version + 1))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="This card has already changed. Reload it before reviewing.")
    db.add(WordStudyReview(card_id=card.id, user_id=user_id, word_id=card.word_id, rating=request.rating,
        reviewed_at=now, review_log=log.to_dict(), before_state=before, after_state=after,
        model_version=schedule.model_version, provenance="card"))
    db.commit()
    db.refresh(schedule)
    return card_response(card, familiarity, schedule)


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, language: Literal["ja", "en"] = "ja", db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    StudyCard, StudyMembership, VocabularyOccurrence, WordStudyFamiliarity, WordStudySchedule, WordStudyReview = _models(language)
    card = _owned_card(db, card_id, user_id, language)
    familiarity = lock_word_study(db, user_id, card.word_id, language)
    membership = db.get(StudyMembership, card.id)
    if familiarity is None or membership is None or not membership.active:
        raise HTTPException(status_code=404, detail="Study membership not active")
    membership.active = False
    membership.removed_at = utc_now()
    schedule = _schedule(db, card.id, language)
    schedule.version += 1
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
