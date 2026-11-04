from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseReading, JapaneseSpelling, JapaneseWordFamiliarity
from app.schemas import GroupToken, UpdateFamiliarityScoreResponse, ParseJapaneseResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.services.japanese_vocab.parser import katakana_to_hiragana
from app.services.japanese_vocab.ranking import RankingCandidate, rank_by_pos_and_frequency

# Kana homophones can have identical POS and conjugation, while JMdict's
# priority tags do not establish which meaning fits a sentence. These defaults
# apply only to reading lookups; an explicit kanji spelling takes precedence.
KANA_VERB_DEFAULTS = {"なる": 1375610}  # 成る: to become

def get_word_id(session: Session, wordToken: GroupToken):
    # Recognized expressions have an explicit JMdict identity, avoiding
    # homophones and the POS of a constituent overriding the expression.
    if wordToken.source_entry_id is not None:
        return session.scalar(select(JapaneseDictionary.word_id).where(
            JapaneseDictionary.source_entry_id == wordToken.source_entry_id
        ))
    if not wordToken.tokens:
        return None

    lookup_form = wordToken.lookup_form
    head = wordToken.tokens[0]
    # Sudachi's reading describes the surface, which may be inflected.
    reading = katakana_to_hiragana(head.katakana_reading) if head.text == lookup_form else ""
    options = (selectinload(JapaneseDictionary.spellings), selectinload(JapaneseDictionary.readings))

    entries = session.scalars(
        select(JapaneseDictionary)
        .join(JapaneseSpelling)
        .where(JapaneseSpelling.spelling == lookup_form)
        .options(*options)
        .order_by(JapaneseDictionary.word_id)
    ).unique().all()
    spelling_match = bool(entries)

    if not entries:
        # Search the dictionary form, not the reading of an inflected surface.
        entries = session.scalars(
            select(JapaneseDictionary)
            .join(JapaneseReading)
            .where(JapaneseReading.reading == lookup_form)
            .options(*options)
            .order_by(JapaneseDictionary.word_id)
        ).unique().all()

    candidates = []
    reading_matches = set()
    for entry in entries:
        spellings = [s for s in entry.spellings if s.spelling == lookup_form] if spelling_match else []
        readings = [
            r for r in entry.readings
            if (not spelling_match or (
                not r.no_kanji and (not r.restricted_spellings or lookup_form in r.restricted_spellings)
            ))
        ]
        if spelling_match and reading:
            matching_readings = [r for r in readings if katakana_to_hiragana(r.reading) == reading]
            if matching_readings:
                reading_matches.add(entry.word_id)
                readings = matching_readings
        elif not spelling_match:
            readings = [r for r in readings if r.reading == lookup_form]

        priorities = {p for form in [*spellings, *readings] for p in (form.priorities or [])}
        parts_of_speech = set()
        inherited_pos = []
        for sense in entry.senses:
            inherited_pos = sense.get("pos") or inherited_pos
            if spelling_match and sense.get("stagk") and lookup_form not in sense["stagk"]:
                continue
            if sense.get("stagr") and not any(r.reading in sense["stagr"] for r in readings):
                continue
            parts_of_speech.update(inherited_pos)
        candidates.append(RankingCandidate(entry.word_id, frozenset(parts_of_speech), frozenset(priorities)))

    if reading_matches:
        candidates = [candidate for candidate in candidates if candidate.word_id in reading_matches]
    ranked = rank_by_pos_and_frequency(
        candidates, head.part_of_speech[0], head.part_of_speech[4]
    )
    if not spelling_match and head.part_of_speech[0] == "動詞":
        default_source_id = KANA_VERB_DEFAULTS.get(lookup_form)
        if default_source_id is not None:
            ids = {entry.word_id for entry in entries if entry.source_entry_id == default_source_id}
            preferred = next((candidate for candidate in ranked if candidate.word_id in ids), None)
            if preferred is not None:
                return preferred.word_id
    return ranked[0].word_id if ranked else None

def get_word_progress(session : Session, word_id: int, user_id : int) :
    familiarity_score = session.scalar(select(JapaneseWordFamiliarity.familiarity_score).where(JapaneseWordFamiliarity.word_id == word_id, JapaneseWordFamiliarity.user_id == user_id))
    if not familiarity_score:
        familiarity_score = 0
    return familiarity_score

def get_word_senses(session : Session, word_id : int):
    return session.scalar(select(JapaneseDictionary.senses).where(JapaneseDictionary.word_id == word_id))

def get_word_details(session: Session, wordToken : GroupToken, user_id : int):
    word_id = get_word_id(session, wordToken)
    if not word_id:
        return None
    familiarity_score = get_word_progress(session, word_id, user_id)
    senses = get_word_senses(session, word_id)

    return ParseJapaneseResponse(word_id=word_id, familiarity_score=familiarity_score, senses=senses)

def update_db_familiarity_score(session : Session, user_id : int, word_id : int, new_score : int) :
    progress = session.get(JapaneseWordFamiliarity, {"user_id":user_id, "word_id":word_id})

    if progress is None:
        progress = JapaneseWordFamiliarity(user_id=user_id, word_id=word_id,familiarity_score=new_score)
        session.add(progress)
    else:
        progress.familiarity_score = new_score

    session.commit()

    return UpdateFamiliarityScoreResponse(word_id=word_id, new_score=new_score)
