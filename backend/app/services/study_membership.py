"""Synchronize word familiarity changes with every related sentence card."""
from fsrs import Card, Scheduler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.study import WordStudyFamiliarity as JapaneseStudyFamiliarity, WordStudySchedule as JapaneseStudySchedule
from app.db.models.english_study import EnglishStudyFamiliarity, EnglishStudySchedule
from app.services.study_policy import eligibility


def lock_word_study(db: Session, user_id: int, word_id: int, language: str = "ja") -> JapaneseStudyFamiliarity | EnglishStudyFamiliarity | None:
    WordStudyFamiliarity = EnglishStudyFamiliarity if language == "en" else JapaneseStudyFamiliarity
    return db.scalar(select(WordStudyFamiliarity).where(
        WordStudyFamiliarity.user_id == user_id, WordStudyFamiliarity.word_id == word_id
    ).with_for_update())


def sync_word_schedules(db: Session, user_id: int, word_id: int, score: int | None, *, exclude_card_id: int | None = None, language: str = "ja") -> None:
    """Recompute each card separately without altering its FSRS memory."""
    WordStudySchedule = EnglishStudySchedule if language == "en" else JapaneseStudySchedule
    schedules = db.scalars(select(WordStudySchedule).where(
        WordStudySchedule.user_id == user_id, WordStudySchedule.word_id == word_id
    ).order_by(WordStudySchedule.card_id)).all()
    for schedule in schedules:
        if schedule.card_id == exclude_card_id:
            continue
        decision = eligibility(Card.from_dict(schedule.serialized_state), Scheduler.from_dict(schedule.scheduler_config), score)
        schedule.review_status = decision.status
        schedule.next_eligible_at = decision.next_eligible_at
        schedule.version += 1


def refresh_manual_familiarity(db: Session, word: JapaneseStudyFamiliarity | EnglishStudyFamiliarity | None, score: int) -> None:
    """Update existing study word only; caller commits familiarity atomically."""
    if word is None:
        return
    word.policy_level = score if score in (1, 2, 3, 4, 5) else None
    word.manual_level = word.policy_level
    word.level_source = "manual" if word.policy_level is not None else None
    sync_word_schedules(db, word.user_id, word.word_id, score, language="en" if isinstance(word, EnglishStudyFamiliarity) else "ja")
