"""Application-level familiarity and review eligibility, separate from FSRS state.

The functions here do not persist data or enroll a word in study. Callers must
apply their results in the same transaction as the review and membership update.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from fsrs import Card, Rating, Scheduler, State


@dataclass(frozen=True)
class StudyPolicy:
    familiar_success_dates: int = 3
    familiar_stability_days: float = 7.0
    very_familiar_success_dates: int = 5
    very_familiar_stability_days: float = 30.0
    return_retrievability: float = 0.8

    def __post_init__(self):
        if not 0 < self.return_retrievability < 1:
            raise ValueError("return_retrievability must be between 0 and 1")
        if self.familiar_success_dates < 1 or self.very_familiar_success_dates < 1:
            raise ValueError("success date requirements must be positive")
        if self.familiar_stability_days <= 0 or self.very_familiar_stability_days <= 0:
            raise ValueError("stability requirements must be positive")


DEFAULT_POLICY = StudyPolicy()


@dataclass(frozen=True)
class Eligibility:
    status: str
    next_eligible_at: datetime | None


def policy_after_review(
    current_level: int | None,
    rating: int | Rating,
    successful_dates: Iterable[date],
    stability: float | None,
    config: StudyPolicy = DEFAULT_POLICY,
) -> int:
    """Return the suggested level after a review using distinct UTC dates.

    ``successful_dates`` includes the current review if it was successful.
    Hard, Good, and Easy are successful recalls; Again is a failure. Unrated
    words begin at level 1 for this calculation. Mastery is always manual.
    """
    if current_level not in (None, 0, 1, 2, 3, 4, 5):
        raise ValueError("familiarity level must be unrated or between 1 and 5")
    grade = Rating(rating)
    level = current_level or 1
    if level == 5:
        return 5
    if grade == Rating.Again:
        return 1 if level <= 2 else 2
    if level == 1:
        return 2
    successful_days = len(set(successful_dates))
    if stability is None:
        return level
    if level == 2 and successful_days >= config.familiar_success_dates and stability >= config.familiar_stability_days:
        return 3
    if level == 3 and successful_days >= config.very_familiar_success_dates and stability >= config.very_familiar_stability_days:
        return 4
    return level


def _threshold_time(card: Card, scheduler: Scheduler, threshold: float) -> datetime:
    """Find the first instant the installed scheduler predicts recall <= threshold.

    py-fsrs 6 uses whole elapsed days in its retrievability calculation. Query
    the scheduler rather than guessing an interval from stability, preserving
    its actual model parameters, rounding and forgetting curve.
    """
    last_review = card.last_review
    if last_review is None or card.stability is None:
        raise ValueError("a reviewed card with memory state is required")
    if last_review.tzinfo is None or last_review.utcoffset() != timedelta(0):
        raise ValueError("last_review must be UTC-aware")
    last_review = last_review.astimezone(timezone.utc)
    max_days = (datetime.max.replace(tzinfo=timezone.utc) - last_review).days

    def reaches(day: int) -> bool:
        return scheduler.get_card_retrievability(card, last_review + timedelta(days=day)) <= threshold

    if reaches(0):
        return last_review
    if max_days == 0:
        raise OverflowError("forgetting threshold exceeds representable datetime")
    lower, upper = 0, 1
    while upper < max_days and not reaches(upper):
        lower, upper = upper, min(upper * 2, max_days)
    if not reaches(upper):
        raise OverflowError("forgetting threshold exceeds representable datetime")
    while lower + 1 < upper:
        middle = (lower + upper) // 2
        if reaches(middle):
            upper = middle
        else:
            lower = middle
    return last_review + timedelta(days=upper)


def eligibility(
    card: Card,
    scheduler: Scheduler,
    level: int | None,
    active: bool = True,
    config: StudyPolicy = DEFAULT_POLICY,
) -> Eligibility:
    """Compute an application due time without changing the FSRS card.

    A caller should filter inactive and mastered memberships out of due
    queries and compare next_eligible_at to its current UTC time. A newly
    enrolled word and all learning/relearning steps use the FSRS due time.
    """
    if level not in (None, -1, 0, 1, 2, 3, 4, 5):
        raise ValueError("familiarity level must be unrated or between 1 and 5")
    if not active:
        return Eligibility("removed", None)
    if level == -1:
        return Eligibility("wont_learn", None)
    if level == 5:
        return Eligibility("mastered", None)
    if level in (3, 4) and card.state == State.Review and card.last_review is not None and card.stability is not None:
        return Eligibility("deferred", _threshold_time(card, scheduler, config.return_retrievability))
    return Eligibility("normal", card.due)
