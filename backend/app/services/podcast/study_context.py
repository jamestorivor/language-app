"""Resolve saved vocabulary snapshots against the current transcript safely."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_access.podcast import get_episode, list_chunks
from app.db.models.study import StudyCard, VocabularyOccurrence


def cue_time(cues: list[dict] | None, start: int, end: int) -> tuple[int | None, int | None]:
    """Use source caption bounds, never inventing a sentence or word timestamp."""
    overlaps = [cue for cue in (cues or []) if cue.get("start_idx", 0) < end and cue.get("end_idx", 0) > start]
    if not overlaps or not (overlaps[0]["start_idx"] <= start < overlaps[0]["end_idx"]):
        return None, None
    if (not (overlaps[-1]["start_idx"] < end <= overlaps[-1]["end_idx"])
            or any(right["start_idx"] - left["end_idx"] > 1 for left, right in zip(overlaps, overlaps[1:]))):
        return overlaps[0].get("start_ms"), None
    start_ms, end_ms = overlaps[0].get("start_ms"), overlaps[-1].get("end_ms")
    if end_ms is not None and start_ms is not None and end_ms <= start_ms:
        end_ms = None
    return start_ms, end_ms


def _matches(chunk, card, occurrence, start):
    """Validate all offsets against the exact saved sentence and surface form."""
    if not chunk.transcript:
        return False
    text = chunk.transcript.text
    relative_start = card.target_start - card.sentence_start
    relative_end = card.target_end - card.sentence_start
    return (0 <= start <= len(text) and text[start:start + len(occurrence.sentence)] == occurrence.sentence
            and 0 <= relative_start < relative_end <= len(occurrence.sentence)
            and occurrence.sentence[relative_start:relative_end] == occurrence.surface_form)


def source_for_card(db: Session, user_id: int, card: StudyCard, occurrence: VocabularyOccurrence) -> dict:
    """Return a snapshot even if the episode is deleted or the card is removed."""
    relative_start = card.target_start - card.sentence_start
    relative_end = card.target_end - card.sentence_start
    result = dict(id=occurrence.id, card_id=card.id, word_id=card.word_id,
                  dictionary_form=card.dictionary_form, episode_id=occurrence.episode_id,
                  episode_title=occurrence.episode_title or card.episode_title,
                  segment_id=None, sentence=occurrence.sentence, target_text=occurrence.surface_form,
                  target_start=relative_start, target_end=relative_end,
                  sentence_start=None, sentence_end=None, transcript_start=None, transcript_end=None,
                  start_ms=occurrence.start_ms, end_ms=occurrence.end_ms,
                  timing="cue" if occurrence.start_ms is not None else "unknown", source_status="missing")
    episode = get_episode(db, user_id, occurrence.episode_id) if occurrence.episode_id is not None else None
    if episode is None:
        return result
    result["episode_title"] = episode.title
    chunks = list_chunks(db, user_id, occurrence.episode_id)
    # Retain the original segment when possible, or locate the replacement by
    # its recorded timestamp.  A timestamp is never invented from chunk bounds.
    original = next((c for c in chunks if c.id == occurrence.segment_id), None)
    timed = next((c for c in chunks if occurrence.start_ms is not None
                  and c.start_time * 1000 <= occurrence.start_ms < c.end_time * 1000), None)
    fallback = original or timed
    result["source_status"] = "changed"
    if fallback:
        result["segment_id"] = fallback.id

    candidates = []
    if original and _matches(original, card, occurrence, card.sentence_start):
        candidates.append((original, card.sentence_start))
    for chunk in ([timed] if timed else chunks):
        if not chunk or not chunk.transcript or not occurrence.sentence:
            continue
        offset = 0
        while True:
            found = chunk.transcript.text.find(occurrence.sentence, offset)
            if found < 0:
                break
            if _matches(chunk, card, occurrence, found) and (chunk, found) not in candidates:
                candidates.append((chunk, found))
            offset = found + 1

    verified = []
    for chunk, start in candidates:
        cue_start, cue_end = cue_time(chunk.transcript.cues, start, start + len(occurrence.sentence))
        if (occurrence.start_ms is None or cue_start == occurrence.start_ms) and (
                occurrence.end_ms is None or cue_end == occurrence.end_ms):
            verified.append((chunk, start))
    # A saved position in the original segment is unambiguous even if the
    # identical sentence appears elsewhere; relocation must be unique.
    preferred = next((item for item in verified if original is not None
                      and item[0].id == original.id and item[1] == card.sentence_start), None)
    resolved = preferred or (verified[0] if len(verified) == 1 else None)
    if resolved is not None:
        chunk, start = resolved
        # A legacy snapshot may predate timestamp storage. A newly imported
        # caption can supply timing only after the exact sentence and target
        # have been verified at a unique source position.
        if occurrence.start_ms is None:
            cue_start, cue_end = cue_time(chunk.transcript.cues, start, start + len(occurrence.sentence))
            if cue_start is not None:
                result.update(start_ms=cue_start, end_ms=cue_end, timing="cue")
        result.update(segment_id=chunk.id, source_status="available", sentence_start=start,
                      sentence_end=start + len(occurrence.sentence), transcript_start=start,
                      transcript_end=start + len(occurrence.sentence))
    return result


def sources_for_word(db: Session, user_id: int, word_id: int, *, card_model=StudyCard, occurrence_model=VocabularyOccurrence) -> list[dict]:
    StudyCard, VocabularyOccurrence = card_model, occurrence_model
    rows = db.execute(select(StudyCard, VocabularyOccurrence).join(
        VocabularyOccurrence, VocabularyOccurrence.card_id == StudyCard.id
    ).where(StudyCard.user_id == user_id, StudyCard.word_id == word_id,
            VocabularyOccurrence.user_id == user_id).order_by(StudyCard.created_at, StudyCard.id)).all()
    return [source_for_card(db, user_id, card, occurrence) for card, occurrence in rows]
