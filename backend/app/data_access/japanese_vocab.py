from collections import defaultdict

from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseReading, JapaneseSpelling, JapaneseWordFamiliarity
from app.schemas import GroupToken, UpdateFamiliarityScoreResponse, ParseJapaneseResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.services.japanese_vocab.parser import katakana_to_hiragana
from app.services.japanese_vocab.ranking import RankingCandidate, rank_by_pos_and_frequency, _pos_matches

# Kana homophones can have identical POS and conjugation, while JMdict's
# priority tags do not establish which meaning fits a sentence. These defaults
# apply only to reading lookups; an explicit kanji spelling takes precedence.
KANA_VERB_DEFAULTS = {"なる": 1375610}  # 成る: to become


def _kana_interjection(token: GroupToken) -> bool:
    form = token.lookup_form
    return bool(token.tokens and token.tokens[0].part_of_speech[0] == "感動詞" and form and all(
        "ぁ" <= char <= "ゟ" or "ァ" <= char <= "ヿ" or char == "ー" for char in form
    ))


def _ordered_senses(token: GroupToken, senses):
    """Show interjection senses first without losing the entry's other senses."""
    if not _kana_interjection(token) or not senses:
        return senses
    inherited = []
    ranked = []
    for sense in senses:
        inherited = sense.get("pos") or inherited
        # A sense limited to another form must not become the primary gloss.
        reading_ok = not sense.get("stagr") or token.lookup_form in sense["stagr"]
        spelling_ok = not sense.get("stagk") or token.lookup_form in sense["stagk"]
        ranked.append((sense, reading_ok and spelling_ok and any(
            _pos_matches("感動詞", pos) for pos in inherited
        )))
    return [sense for sense, matches in ranked if matches] + [sense for sense, matches in ranked if not matches]


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
    options = (selectinload(JapaneseDictionary.spellings), selectinload(JapaneseDictionary.readings))

    entries = session.scalars(
        select(JapaneseDictionary)
        .join(JapaneseSpelling)
        .where(JapaneseSpelling.spelling == lookup_form)
        .options(*options)
        .order_by(JapaneseDictionary.word_id)
    ).unique().all()
    spelling_match = bool(entries)

    reading_entries = []
    if not entries or _kana_interjection(wordToken):
        # Search the dictionary form, not the reading of an inflected surface.
        reading_entries = session.scalars(
            select(JapaneseDictionary)
            .join(JapaneseReading)
            .where(JapaneseReading.reading == lookup_form)
            .options(*options)
            .order_by(JapaneseDictionary.word_id)
        ).unique().all()

    if not entries:
        return _rank_word_id(wordToken, reading_entries, False)
    return _rank_word_id(wordToken, entries, spelling_match, reading_entries)


def _rank_word_id(wordToken: GroupToken, entries, spelling_match: bool, reading_entries=()):
    lookup_form = wordToken.lookup_form
    head = wordToken.tokens[0]
    reading = katakana_to_hiragana(head.katakana_reading) if head.text == lookup_form else ""
    candidates = []
    reading_matches = set()
    for entry, is_spelling in [(entry, spelling_match) for entry in entries] + [(entry, False) for entry in reading_entries]:
        spellings = [s for s in entry.spellings if s.spelling == lookup_form] if is_spelling else []
        readings = [
            r for r in entry.readings
            if (not is_spelling or (
                not r.no_kanji and (not r.restricted_spellings or lookup_form in r.restricted_spellings)
            ))
        ]
        if is_spelling and reading:
            matching_readings = [r for r in readings if katakana_to_hiragana(r.reading) == reading]
            if matching_readings:
                reading_matches.add(entry.word_id)
                readings = matching_readings
        elif not is_spelling:
            readings = [r for r in readings if r.reading == lookup_form]

        priorities = {p for form in [*spellings, *readings] for p in (form.priorities or [])}
        parts_of_speech = set()
        inherited_pos = []
        for sense in entry.senses:
            inherited_pos = sense.get("pos") or inherited_pos
            if is_spelling and sense.get("stagk") and lookup_form not in sense["stagk"]:
                continue
            if sense.get("stagr") and not any(r.reading in sense["stagr"] for r in readings):
                continue
            parts_of_speech.update(inherited_pos)
        candidates.append(RankingCandidate(entry.word_id, frozenset(parts_of_speech), frozenset(priorities)))

    if reading_matches and not reading_entries:
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
    senses = _ordered_senses(wordToken, get_word_senses(session, word_id))

    return ParseJapaneseResponse(word_id=word_id, familiarity_score=familiarity_score, senses=senses)

# Keep batches bounded for database parameter limits and large transcripts.
QUERY_BATCH_SIZE = 300


def _batches(values):
    values = list(values)
    for offset in range(0, len(values), QUERY_BATCH_SIZE):
        yield values[offset:offset + QUERY_BATCH_SIZE]


def get_word_details_batch(session: Session, word_tokens: list[GroupToken], user_id: int):
    """Resolve each group in order while fetching dictionary data in batches."""
    source_ids = {token.source_entry_id for token in word_tokens if token.source_entry_id is not None}
    forms = {token.lookup_form for token in word_tokens if token.source_entry_id is None and token.tokens}
    by_source = {}
    spellings = defaultdict(list)
    readings = defaultdict(list)
    options = (selectinload(JapaneseDictionary.spellings), selectinload(JapaneseDictionary.readings))

    for batch in _batches(source_ids):
        for entry in session.scalars(select(JapaneseDictionary).where(JapaneseDictionary.source_entry_id.in_(batch))):
            by_source[entry.source_entry_id] = entry

    for batch in _batches(forms):
        rows = session.execute(
            select(JapaneseSpelling.spelling, JapaneseDictionary)
            .join(JapaneseSpelling, JapaneseSpelling.word_id == JapaneseDictionary.word_id)
            .where(JapaneseSpelling.spelling.in_(batch))
            .options(*options)
            .order_by(JapaneseDictionary.word_id)
        ).unique()
        for form, entry in rows:
            spellings[form].append(entry)

    reading_forms = (forms - spellings.keys()) | {token.lookup_form for token in word_tokens if _kana_interjection(token)}
    for batch in _batches(reading_forms):
        rows = session.execute(
            select(JapaneseReading.reading, JapaneseDictionary)
            .join(JapaneseReading, JapaneseReading.word_id == JapaneseDictionary.word_id)
            .where(JapaneseReading.reading.in_(batch))
            .options(*options)
            .order_by(JapaneseDictionary.word_id)
        ).unique()
        for form, entry in rows:
            readings[form].append(entry)

    entries_by_id = {entry.word_id: entry for entry in by_source.values()}
    for candidates in (*spellings.values(), *readings.values()):
        entries_by_id.update((entry.word_id, entry) for entry in candidates)

    resolved_ids = []
    for token in word_tokens:
        if token.source_entry_id is not None:
            entry = by_source.get(token.source_entry_id)
            word_id = entry.word_id if entry else None
        elif token.tokens:
            candidates = spellings.get(token.lookup_form) or readings.get(token.lookup_form, [])
            extra_readings = readings.get(token.lookup_form, []) if _kana_interjection(token) and spellings.get(token.lookup_form) else ()
            word_id = _rank_word_id(token, candidates, bool(spellings.get(token.lookup_form)), extra_readings)
        else:
            word_id = None
        resolved_ids.append(word_id)

    progress = {}
    for batch in _batches({word_id for word_id in resolved_ids if word_id is not None}):
        rows = session.execute(select(JapaneseWordFamiliarity.word_id, JapaneseWordFamiliarity.familiarity_score)
                               .where(JapaneseWordFamiliarity.user_id == user_id,
                                      JapaneseWordFamiliarity.word_id.in_(batch)))
        progress.update(rows.all())

    return [
        ParseJapaneseResponse(word_id=word_id, familiarity_score=progress.get(word_id, 0),
                              senses=_ordered_senses(token, entries_by_id[word_id].senses))
        if word_id is not None else None
        for token, word_id in zip(word_tokens, resolved_ids, strict=True)
    ]


def update_db_familiarity_score(session : Session, user_id : int, word_id : int, new_score : int) :
    progress = session.get(JapaneseWordFamiliarity, {"user_id":user_id, "word_id":word_id})

    if progress is None:
        progress = JapaneseWordFamiliarity(user_id=user_id, word_id=word_id,familiarity_score=new_score)
        session.add(progress)
    else:
        progress.familiarity_score = new_score

    session.commit()

    return UpdateFamiliarityScoreResponse(word_id=word_id, new_score=new_score)
