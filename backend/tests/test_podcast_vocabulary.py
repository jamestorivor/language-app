"""Coverage reflects known word occurrences without assuming uncertain words are unknown."""

from hashlib import sha256
from types import SimpleNamespace

from app.services.podcast.vocabulary import analyze_chunk, estimate, summarize


def test_coverage_counts_known_occurrences_and_retains_uncertainty():
    # Repeated words count repeatedly; ratings 0, 1 and 2 are not evidence
    # that a word's meaning is unknown. Unmatched groups are uncertain too.
    counts = {"a": 2, "b": 1, "c": 3, "d": 1, "e": 1, "f": 1}
    ratings = {"a": 3, "b": 4, "c": 5, "d": 1, "e": 2}
    result = estimate(counts, ratings, unmatched=1)

    assert result["coverage_low"] == 60.0
    assert result["coverage_high"] == 100.0


def test_coverage_is_fully_known_when_every_occurrence_is_rated_three_or_higher():
    result = estimate({"a": 1, "b": 2, "c": 3}, {"a": 3, "b": 4, "c": 5}, unmatched=0)

    assert result["coverage_low"] == 100.0
    assert result["coverage_high"] == 100.0


def test_coverage_does_not_lose_transcripts_with_only_unmatched_words():
    result = estimate({}, {}, unmatched=4)

    assert result["coverage_low"] == 0.0
    assert result["coverage_high"] == 100.0
    assert estimate({}, {}, unmatched=0) is None


def test_wont_learn_is_uncertain_and_not_a_familiarity_rating():
    result = estimate({"skipped": 2, "known": 1}, {"skipped": -1, "known": 5}, unmatched=0)

    assert result["coverage_low"] == 33.3
    assert result["uncertain_occurrences"] == 2
    assert result["unrated_unique"] == 1
    assert result["rated_percent"] == 33.3


def test_wont_learn_transitions_are_not_familiarity_changes():
    result = summarize(
        {"skip": 1, "resume": 1, "improve": 1, "decline": 1, "new_skip": 1}, 0,
        {"skip": 4, "resume": -1, "improve": 2, "decline": 4},
        {"skip": -1, "resume": 3, "improve": 3, "decline": 2, "new_skip": -1},
    )

    assert result["improved_unique"] == 1
    assert result["declined_unique"] == 1
    assert result["newly_rated_unique"] == 1


def test_analysis_refreshes_legacy_cache_and_includes_hidden_japanese_groups(monkeypatch):
    transcript = "猫は未知。"
    old_fingerprint = sha256(("v1\0ja\0" + transcript).encode()).hexdigest()
    cached = SimpleNamespace(fingerprint=old_fingerprint, counts={"10": 1}, unmatched=0)
    chunk = SimpleNamespace(id=1, user_id=1, transcript=SimpleNamespace(text=transcript))
    calls = []

    def parse(session, text, user_id, language):
        calls.append(text)
        return [
            SimpleNamespace(word_id=10, display=True, text="猫"),
            SimpleNamespace(word_id=11, display=False, text="は"),
            SimpleNamespace(word_id=None, display=False, text="未知"),
            SimpleNamespace(word_id=None, display=False, text="。"),
        ]

    monkeypatch.setattr("app.services.podcast.vocabulary.parse_groups", parse)
    counts, unmatched = analyze_chunk(None, chunk, "ja", cached)
    assert counts == {"10": 1, "11": 1}
    assert unmatched == 1
    assert cached.fingerprint != old_fingerprint
    assert analyze_chunk(None, chunk, "ja", cached) == (counts, unmatched)
    assert calls == [transcript]
