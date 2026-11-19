from datetime import date, datetime, timedelta, timezone

import pytest
from fsrs import Card, Rating, Scheduler, State

from app.services.study_policy import StudyPolicy, eligibility, policy_after_review


@pytest.mark.parametrize("rating,expected", [
    (Rating.Again, 1), (Rating.Hard, 2), (Rating.Good, 2), (Rating.Easy, 2),
])
def test_level_one_progresses_after_successful_recall(rating, expected):
    assert policy_after_review(1, rating, [], 1.0) == expected


@pytest.mark.parametrize("dates,stability,expected", [
    ([date(2026, 1, 1), date(2026, 1, 2)], 30.0, 2),
    ([date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)], 6.99, 2),
    ([date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)], 7.0, 3),
    ([date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 2)], 30.0, 2),
])
def test_level_two_requires_three_distinct_days_and_seven_days_stability(dates, stability, expected):
    assert policy_after_review(2, Rating.Good, dates, stability) == expected


@pytest.mark.parametrize("dates,stability,expected", [
    ([date(2026, 1, day) for day in range(1, 5)], 90.0, 3),
    ([date(2026, 1, day) for day in range(1, 6)], 29.99, 3),
    ([date(2026, 1, day) for day in range(1, 6)], 30.0, 4),
])
def test_level_three_requires_five_days_and_thirty_days_stability(dates, stability, expected):
    assert policy_after_review(3, Rating.Easy, dates, stability) == expected


@pytest.mark.parametrize("level,expected", [(1, 1), (2, 1), (3, 2), (4, 2), (5, 5)])
def test_again_demotes_without_promoting_or_reactivating_mastered_words(level, expected):
    dates = [date(2026, 1, day) for day in range(1, 8)]
    assert policy_after_review(level, Rating.Again, dates, 90.0) == expected


@pytest.mark.parametrize("rating", [Rating.Hard, Rating.Good, Rating.Easy])
def test_successful_ratings_contribute_to_progress_at_level_two(rating):
    dates = [date(2026, 1, day) for day in range(1, 4)]
    assert policy_after_review(2, rating, dates, 7.0) == 3


def test_progression_advances_only_one_level_and_never_sets_mastery():
    dates = [date(2026, 1, day) for day in range(1, 9)]
    assert policy_after_review(1, Rating.Easy, dates, 90.0) == 2
    assert policy_after_review(2, Rating.Easy, dates, 90.0) == 3
    assert policy_after_review(3, Rating.Easy, dates, 90.0) == 4
    assert policy_after_review(4, Rating.Easy, dates, 90.0) == 4


def test_familiar_words_wait_until_actual_retrievability_reaches_eighty_percent():
    last_review = datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
    scheduler = Scheduler(enable_fuzzing=False)
    card = Card(card_id=1, state=State.Review, step=None, stability=10.0,
                difficulty=5.0, last_review=last_review, due=last_review + timedelta(days=10))
    for level in (3, 4):
        decision = eligibility(card, scheduler, level)
        assert decision.status == "deferred"
        assert decision.next_eligible_at > card.due
        assert scheduler.get_card_retrievability(card, decision.next_eligible_at) <= 0.8
        assert scheduler.get_card_retrievability(card, decision.next_eligible_at - timedelta(seconds=1)) > 0.8
    for level in (1, 2):
        decision = eligibility(card, scheduler, level)
        assert decision.status == "normal"
        assert decision.next_eligible_at == card.due


@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_new_and_relearning_cards_keep_normal_fsrs_steps(level):
    due = datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
    scheduler = Scheduler(enable_fuzzing=False)
    for card in (
        Card(card_id=1, state=State.Learning, due=due),
        Card(card_id=2, state=State.Relearning, step=0, stability=10.0,
             difficulty=5.0, last_review=due - timedelta(days=1), due=due),
    ):
        decision = eligibility(card, scheduler, level)
        assert decision.status == "normal"
        assert decision.next_eligible_at == due


def test_mastered_and_removed_cards_have_no_due_review():
    card = Card(card_id=1, due=datetime(2026, 1, 1, tzinfo=timezone.utc))
    scheduler = Scheduler(enable_fuzzing=False)
    assert eligibility(card, scheduler, 5).status == "mastered"
    assert eligibility(card, scheduler, 5).next_eligible_at is None
    assert eligibility(card, scheduler, -1).status == "wont_learn"
    assert eligibility(card, scheduler, -1).next_eligible_at is None
    assert eligibility(card, scheduler, 1, active=False).status == "removed"
    assert eligibility(card, scheduler, 1, active=False).next_eligible_at is None


def test_policy_settings_change_progression_and_retention_threshold():
    policy = StudyPolicy(familiar_success_dates=2, familiar_stability_days=4,
                         return_retrievability=0.7)
    assert policy_after_review(2, Rating.Good, [date(2026, 1, 1), date(2026, 1, 2)], 4.0, policy) == 3
    last_review = datetime(2026, 1, 1, tzinfo=timezone.utc)
    card = Card(card_id=1, state=State.Review, step=None, stability=10.0,
                difficulty=5.0, last_review=last_review, due=last_review + timedelta(days=10))
    scheduler = Scheduler(enable_fuzzing=False)
    regular = eligibility(card, scheduler, 3)
    changed = eligibility(card, scheduler, 3, config=policy)
    assert changed.next_eligible_at > regular.next_eligible_at
    assert scheduler.get_card_retrievability(card, changed.next_eligible_at) <= 0.7


def test_review_phase_uses_eighty_percent_even_if_fsrs_due_is_later():
    last_review = datetime(2026, 1, 1, tzinfo=timezone.utc)
    card = Card(card_id=1, state=State.Review, step=None, stability=10.0,
                difficulty=5.0, last_review=last_review, due=last_review + timedelta(days=365))
    scheduler = Scheduler(enable_fuzzing=False)
    decision = eligibility(card, scheduler, 3)
    assert decision.next_eligible_at < card.due
    assert scheduler.get_card_retrievability(card, decision.next_eligible_at) <= 0.8
    assert scheduler.get_card_retrievability(card, decision.next_eligible_at - timedelta(seconds=1)) > 0.8


@pytest.mark.parametrize("level", [None, 0])
def test_unrated_uses_initial_familiarity_policy_without_inventing_history(level):
    assert policy_after_review(level, Rating.Again, [], None) == 1
    assert policy_after_review(level, Rating.Good, [date(2026, 1, 1)], 1.0) == 2
    card = Card(card_id=1, due=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert eligibility(card, Scheduler(enable_fuzzing=False), level).next_eligible_at == card.due


def test_missing_memory_state_never_delays_review():
    due = datetime(2026, 1, 1, tzinfo=timezone.utc)
    card = Card(card_id=1, state=State.Review, step=None, stability=None,
                difficulty=None, last_review=None, due=due)
    decision = eligibility(card, Scheduler(enable_fuzzing=False), 3)
    assert decision.status == "normal"
    assert decision.next_eligible_at == due


@pytest.mark.parametrize("level", [-2, 6])
def test_invalid_familiarity_levels_are_rejected(level):
    with pytest.raises(ValueError):
        policy_after_review(level, Rating.Good, [], 1.0)
    with pytest.raises(ValueError):
        eligibility(Card(card_id=1), Scheduler(enable_fuzzing=False), level)
