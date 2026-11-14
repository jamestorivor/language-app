"""Transcript-based vocabulary estimates and their historical baseline."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.english_vocab import EnglishWordFamiliarity
from app.db.models.japanese_vocab import JapaneseWordFamiliarity
from app.db.models.podcast import PodcastChunk, PodcastEpisode, PodcastVocabularyBaseline, PodcastVocabularyAnalysis
from app.services.english_vocab import parse_english_text
from app.services.japanese_vocab.parser import parse_japanese_text
from app.services.japanese_vocab.grouping import regroup_tokens, add_db_data_to_tokens
from app.services.japanese_vocab.dictionary_expressions import find_dictionary_expressions

WEIGHTS = {1: 0.1, 2: 0.3, 3: 0.6, 4: 0.8, 5: 1.0}


def ratings(session: Session, user_id: int, language: str) -> dict[str, int]:
    model = EnglishWordFamiliarity if language == "en" else JapaneseWordFamiliarity
    return {str(word): score for word, score in session.execute(
        select(model.word_id, model.familiarity_score).where(model.user_id == user_id)
    )}


def reset_baseline(session: Session, episode, has_transcript: bool):
    """Capture ratings at transcript creation/replacement, before later edits."""
    session.execute(delete(PodcastVocabularyBaseline).where(PodcastVocabularyBaseline.episode_id == episode.id))
    if has_transcript:
        session.add(PodcastVocabularyBaseline(episode_id=episode.id, user_id=episode.user_id,
            language=episode.language, scores=ratings(session, episode.user_id, episode.language),
            captured_at=datetime.now(timezone.utc)))


def parse_groups(session: Session, text: str, user_id: int, language: str):
    if language == "en":
        return parse_english_text(session, text, user_id)
    tokens = parse_japanese_text(text)
    groups = regroup_tokens(text, tokens, find_dictionary_expressions(session, tokens))
    return add_db_data_to_tokens(session, groups, user_id)


def analyze_chunk(session: Session, chunk, language: str, cached):
    text = chunk.transcript.text if chunk.transcript else ""
    if not text.strip():
        return {}, 0
    # Bump the version if token matching or counting rules change.
    fingerprint = sha256(("v2\0" + language + "\0" + text).encode()).hexdigest()
    if cached and cached.fingerprint == fingerprint:
        return cached.counts, cached.unmatched
    groups = parse_groups(session, text, chunk.user_id, language)
    # Include matched lexical groups even when they are hidden in the transcript
    # UI (for example, Japanese particles). Expressions remain single groups.
    lexical = [group for group in groups if any(c.isalnum() for c in group.text)]
    counts = Counter(str(group.word_id) for group in lexical if group.word_id is not None)
    unmatched = sum(1 for group in lexical if group.word_id is None)
    if cached is None:
        cached = PodcastVocabularyAnalysis(chunk_id=chunk.id, fingerprint=fingerprint, counts=dict(counts), unmatched=unmatched)
        session.add(cached)
    else:
        cached.fingerprint, cached.counts, cached.unmatched = fingerprint, dict(counts), unmatched
    return dict(counts), unmatched


def estimate(counts: dict[str, int], scores: dict[str, int], unmatched: int):
    total = sum(counts.values())
    coverage_total = total + unmatched
    if not coverage_total:
        return None
    rated = sum(n for word, n in counts.items() if scores.get(word, 0) in WEIGHTS)
    points = sum(n * WEIGHTS.get(scores.get(word, 0), 0) for word, n in counts.items())
    # Retain the legacy weighted familiarity values for existing clients. With
    # no matched groups they have no rated evidence, so use the full range.
    lower = 100 * points / total if total else 0
    upper = lower + 100 * (total - rated) / total if total else 100
    # Ratings 3–5 imply use of the word, while 0–2 and unmatched groups do
    # not establish whether its meaning is known. These are assumption-based
    # bounds, not a statistical confidence interval or listening score.
    known = sum(n for word, n in counts.items() if scores.get(word, 0) in (3, 4, 5))
    return {
        # Round the lower bound down so rounding cannot exclude the raw value.
        "coverage_low": (1000 * known // coverage_total) / 10, "coverage_high": 100.0,
        "known_occurrences": known, "uncertain_occurrences": coverage_total - known,
        "coverage_occurrences": coverage_total,
        "uncertain_rated_unique": sum(1 for word in counts if scores.get(word, 0) in (1, 2)),
        "familiarity_low": round(lower, 1), "familiarity_high": round(upper, 1),
        "difficulty_low": round(100 - upper, 1),
        "difficulty_high": round(100 - lower, 1),
        "rated_percent": round(100 * rated / total, 1) if total else 0, "matched_occurrences": total,
        "unmatched_groups": unmatched,
        "dictionary_match_percent": round(100 * total / coverage_total, 1),
        "unrated_unique": sum(1 for word in counts if not scores.get(word, 0)),
        "low_rated_unique": sum(1 for word in counts if scores.get(word, 0) in (1, 2)),
    }


def summarize(counts, unmatched, baseline, current):
    before = estimate(counts, baseline, unmatched)
    now = estimate(counts, current, unmatched)
    return {"baseline": before, "current": now,
        "improved_unique": sum(1 for word in counts if baseline.get(word, 0) and current.get(word, 0) > baseline[word]),
        "declined_unique": sum(1 for word in counts if current.get(word, 0) and baseline.get(word, 0) > current[word]),
        "newly_rated_unique": sum(1 for word in counts if not baseline.get(word, 0) and current.get(word, 0))}


def episode_summary(session: Session, episode, chunks):
    # Serialize first-time analysis and cache creation for the same episode.
    session.execute(select(PodcastEpisode.id).where(PodcastEpisode.id == episode.id).with_for_update()).scalar_one()
    baseline = session.get(PodcastVocabularyBaseline, episode.id)
    # Episodes created before this feature get a clearly dated baseline on first analysis.
    if baseline is None and any(c.transcript and c.transcript.text.strip() for c in chunks):
        reset_baseline(session, episode, True)
        session.flush()
        baseline = session.get(PodcastVocabularyBaseline, episode.id)
    if baseline is None:
        return {"added_at": episode.added_at, "baseline_at": None, "episode": None, "segments": {}, "segments_with_text": 0, "segment_count": len(chunks)}
    current = ratings(session, episode.user_id, episode.language)
    total_counts = Counter()
    total_unmatched = 0
    segments = {}
    cached = {analysis.chunk_id: analysis for analysis in session.scalars(
        select(PodcastVocabularyAnalysis).join(PodcastChunk, PodcastChunk.id == PodcastVocabularyAnalysis.chunk_id)
        .where(PodcastChunk.podcast_id == episode.id, PodcastChunk.user_id == episode.user_id)
    )}
    for chunk in chunks:
        counts, unmatched = analyze_chunk(session, chunk, episode.language, cached.get(chunk.id))
        total_counts.update(counts)
        total_unmatched += unmatched
        segments[str(chunk.id)] = summarize(counts, unmatched, baseline.scores, current)
    result = {"added_at": episode.added_at, "baseline_at": baseline.captured_at.isoformat(),
              "episode": summarize(total_counts, total_unmatched, baseline.scores, current), "segments": segments,
              "segments_with_text": sum(1 for c in chunks if c.transcript and c.transcript.text.strip()), "segment_count": len(chunks)}
    session.commit()
    return result
