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
# Reviewed defaults for ordinary spoken kana. These are fallbacks, not claims
# that a reading can never mean something else. Explicit kanji always wins.
KANA_DEFAULTS = {
    ("なる", "動詞"): 1375610,  # 成る: become
    ("する", "動詞"): 1157170,  # 為る: do
    ("いける", "動詞"): 1631370,  # 行ける: can go / works
    ("なくなる", "動詞"): 1529550,  # 無くなる: disappear / run out
    ("つまる", "動詞"): 1226480,  # 詰まる: be packed / clogged
    ("こと", "名詞"): 1313580,  # 事: matter
    ("もの", "名詞"): 1502390,  # 物: thing
}

# JMdict form priorities are not sense frequencies. Prefer these common spoken
# senses within the selected entry, retaining the other senses for inspection.
# Match on gloss text rather than list position so source updates can reorder.
SPOKEN_SENSE_DEFAULTS = {
    1374550: "amazing",
    1190860: "strange",
    1009320: "rapidly",
}

def _lookup_forms(token: GroupToken):
    # A complete explicitly written dictionary form can correct a tokenizer's
    # mistaken lemma (e.g. 生ける analysed as 生く + る). Kana remains lemma-
    # first because it is often ambiguous with an inflection.
    surface = token.text
    has_negative_auxiliary = any(t.dictionary_form == "ない" and t.part_of_speech[0] == "助動詞"
                                 for t in token.tokens[1:])
    forms = (surface, token.lookup_form, token.tokens[0].text) if not _is_kana_form(surface) and not has_negative_auxiliary else (
        token.lookup_form, surface, token.tokens[0].text
    )
    return list(dict.fromkeys(forms))


def _applicable_senses(entry, lookup_form, reading, spelling_match):
    """Apply JMdict form restrictions and inherit omitted POS tags."""
    allowed_readings = [r for r in entry.readings if (
        (not spelling_match and r.reading == lookup_form)
        or (spelling_match and not getattr(r, "no_kanji", False)
            and (not getattr(r, "restricted_spellings", None)
                 or lookup_form in r.restricted_spellings))
    )]
    matching = [r for r in allowed_readings if katakana_to_hiragana(r.reading) == reading]
    if matching:
        allowed_readings = matching
    inherited_pos = []
    senses = []
    for sense in entry.senses:
        inherited_pos = sense.get("pos") or inherited_pos
        if spelling_match and sense.get("stagk") and lookup_form not in sense["stagk"]:
            continue
        if sense.get("stagr") and not any(r.reading in sense["stagr"] for r in allowed_readings):
            continue
        senses.append((sense, inherited_pos))
    return senses, allowed_readings


def _rank_word_id(wordToken: GroupToken, entries, spelling_match: bool, *, lookup_form=None, require_pos=False, return_candidates=False):
    lookup_form = lookup_form or wordToken.lookup_form
    head = wordToken.tokens[0]
    lookup_pos = _lookup_pos(wordToken, lookup_form)
    reading = katakana_to_hiragana(head.katakana_reading) if head.text == lookup_form else ""
    candidates = []
    reading_matches = set()
    for entry in entries:
        senses, readings = _applicable_senses(entry, lookup_form, reading, spelling_match)
        parts_of_speech = {pos for _, tags in senses for pos in tags}
        if require_pos and not any(_pos_matches(lookup_pos, pos) for pos in parts_of_speech):
            continue
        if spelling_match and any(katakana_to_hiragana(r.reading) == reading for r in readings):
            reading_matches.add(entry.word_id)
        spellings = [s for s in entry.spellings if s.spelling == lookup_form] if spelling_match else []
        priorities = {p for form in [*spellings, *readings] for p in (form.priorities or [])}
        candidates.append(RankingCandidate(entry.word_id, frozenset(parts_of_speech), frozenset(priorities)))
    if reading_matches:
        candidates = [candidate for candidate in candidates if candidate.word_id in reading_matches]
    ranked = rank_by_pos_and_frequency(candidates, lookup_pos, head.part_of_speech[4])
    if not spelling_match:
        default_source_id = KANA_DEFAULTS.get((lookup_form, head.part_of_speech[0]))
        if default_source_id is not None:
            ids = {entry.word_id for entry in entries if getattr(entry, "source_entry_id", None) == default_source_id}
            preferred = next((candidate for candidate in ranked if candidate.word_id in ids), None)
            if preferred is not None:
                ranked.remove(preferred)
                ranked.insert(0, preferred)
    if return_candidates:
        return ranked
    return ranked[0].word_id if ranked else None


def _is_kana_form(form):
    return bool(form) and all("ぁ" <= char <= "ゟ" or "ァ" <= char <= "ヿ" or char == "ー" for char in form)


def _lookup_pos(token, form):
    # Sudachi often tags the hesitation あの as a prenominal determiner.
    if form == "あの" and token._followed_by_pause:
        return "感動詞"
    return token.tokens[0].part_of_speech[0]


def _resolve_token(token, spellings, readings):
    for form in _lookup_forms(token):
        for require_pos in (True, False):
            written = _rank_word_id(token, spellings.get(form, []), True, lookup_form=form,
                                    require_pos=require_pos, return_candidates=True)
            read = _rank_word_id(token, readings.get(form, []), False, lookup_form=form,
                                 require_pos=require_pos, return_candidates=True)
            # Explicit kanji identifies a written entry. Kana spellings and
            # readings are equivalent lookup paths, so rank them together.
            if written and not _is_kana_form(form):
                ranked = [(candidate, True) for candidate in written]
            else:
                variants = {}
                for candidate, is_spelling in [(c, True) for c in written] + [(c, False) for c in read]:
                    existing = variants.get(candidate.word_id)
                    if existing:
                        previous, previous_spelling = existing
                        candidate = RankingCandidate(candidate.word_id,
                            previous.parts_of_speech | candidate.parts_of_speech,
                            previous.priorities | candidate.priorities)
                        is_spelling = previous_spelling
                    variants[candidate.word_id] = candidate, is_spelling
                ranked_candidates = rank_by_pos_and_frequency(
                    [candidate for candidate, _ in variants.values()],
                    _lookup_pos(token, form), token.tokens[0].part_of_speech[4],
                )
                ranked = [(candidate, variants[candidate.word_id][1]) for candidate in ranked_candidates]
                # Apply reviewed kana defaults after merging both lookup paths.
                default_source_id = KANA_DEFAULTS.get((form, token.tokens[0].part_of_speech[0]))
                ids = {entry.word_id for entry in [*spellings.get(form, []), *readings.get(form, [])]
                       if getattr(entry, "source_entry_id", None) == default_source_id}
                if default_source_id is not None:
                    ranked.sort(key=lambda item: item[0].word_id not in ids)
            if ranked:
                alternatives = [(candidate.word_id, is_spelling) for candidate, is_spelling in ranked]
                return ranked[0][0].word_id, form, ranked[0][1], require_pos, alternatives
    return None


def _selected_senses(entry, token, form, spelling_match, filter_pos):
    head = token.tokens[0]
    senses, _ = _applicable_senses(entry, form, katakana_to_hiragana(head.katakana_reading) if head.text == form else "", spelling_match)
    applicable = [sense for sense, _ in senses]
    compatible = [sense for sense, tags in senses if any(_pos_matches(_lookup_pos(token, form), pos) for pos in tags)] if filter_pos else applicable
    # JMdict priority markers describe forms, not the order of meanings within
    # an entry. Sudachi calls conversational まあ an adverb; select its
    # reviewed hesitation sense when present, leaving the other meanings.
    if form in {"まあ", "ま"} and token._followed_by_pause and (
        head.part_of_speech[0] == "副詞" or head.part_of_speech[1] == "フィラー"
    ):
        # A shortened ま is tagged as an interjection, but the hesitation
        # sense is tagged as an adverb in JMdict.
        compatible = applicable
        compatible.sort(key=lambda sense: not any(
            "hesitating to express an opinion" in note for note in sense.get("s_inf", [])
        ))
    if form == "はあ" and token._followed_by_pause:
        compatible.sort(key=lambda sense: "sigh" not in sense.get("glosses", []))
    preferred_gloss = SPOKEN_SENSE_DEFAULTS.get(getattr(entry, "source_entry_id", None))
    if preferred_gloss:
        compatible.sort(key=lambda sense: not any(preferred_gloss in gloss.casefold() for gloss in sense.get("glosses", [])))
    return compatible or applicable


def get_word_id(session: Session, wordToken: GroupToken):
    if wordToken.source_entry_id is not None:
        return session.scalar(select(JapaneseDictionary.word_id).where(
            JapaneseDictionary.source_entry_id == wordToken.source_entry_id
        ))
    if not wordToken.tokens:
        return None
    options = (selectinload(JapaneseDictionary.spellings), selectinload(JapaneseDictionary.readings))
    for form in _lookup_forms(wordToken):
        spellings = session.scalars(select(JapaneseDictionary).join(JapaneseSpelling)
            .where(JapaneseSpelling.spelling == form).options(*options)
            .order_by(JapaneseDictionary.word_id)).unique().all()
        word_id = _rank_word_id(wordToken, spellings, True, lookup_form=form, require_pos=True)
        if word_id is not None and not _is_kana_form(form):
            return word_id
        readings = session.scalars(select(JapaneseDictionary).join(JapaneseReading)
            .where(JapaneseReading.reading == form).options(*options)
            .order_by(JapaneseDictionary.word_id)).unique().all()
        resolved = _resolve_token(wordToken, {form: spellings}, {form: readings})
        if resolved:
            return resolved[0]
    return None

def get_word_progress(session : Session, word_id: int, user_id : int) :
    familiarity_score = session.scalar(select(JapaneseWordFamiliarity.familiarity_score).where(JapaneseWordFamiliarity.word_id == word_id, JapaneseWordFamiliarity.user_id == user_id))
    if not familiarity_score:
        familiarity_score = 0
    return familiarity_score

def get_word_senses(session : Session, word_id : int):
    return session.scalar(select(JapaneseDictionary.senses).where(JapaneseDictionary.word_id == word_id))

def get_word_details(session: Session, wordToken: GroupToken, user_id: int):
    return get_word_details_batch(session, [wordToken], user_id)[0]

# Keep batches bounded for database parameter limits and large transcripts.
QUERY_BATCH_SIZE = 300


def _batches(values):
    values = list(values)
    for offset in range(0, len(values), QUERY_BATCH_SIZE):
        yield values[offset:offset + QUERY_BATCH_SIZE]


def get_word_details_batch(session: Session, word_tokens: list[GroupToken], user_id: int):
    """Resolve each group in order while fetching dictionary data in batches."""
    source_ids = {token.source_entry_id for token in word_tokens if token.source_entry_id is not None}
    forms = {form for token in word_tokens if token.source_entry_id is None and token.tokens for form in _lookup_forms(token)}
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

    # A compatible written form already identifies the entry without a
    # reading query. Otherwise include readings even when spellings exist.
    reading_forms = {
        form for token in word_tokens if token.source_entry_id is None and token.tokens
        for form in _lookup_forms(token)
        if _is_kana_form(form) or _rank_word_id(token, spellings.get(form, []), True, lookup_form=form, require_pos=True) is None
    }
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
    resolved_senses = []
    for token in word_tokens:
        if token.source_entry_id is not None:
            entry = by_source.get(token.source_entry_id)
            word_id = entry.word_id if entry else None
            senses = entry.senses if entry else None
        elif token.tokens:
            resolved = _resolve_token(token, spellings, readings)
            word_id = resolved[0] if resolved else None
            senses = []
            if resolved:
                _, form, is_spelling, filter_pos, _ = resolved
                # A word ID and its definitions must refer to the same entry;
                # other homophones cannot be presented as its senses.
                senses = _selected_senses(entries_by_id[word_id], token, form, is_spelling, filter_pos)
            else:
                senses = None
        else:
            word_id = None
            senses = None
        resolved_ids.append(word_id)
        resolved_senses.append(senses)

    progress = {}
    for batch in _batches({word_id for word_id in resolved_ids if word_id is not None}):
        rows = session.execute(select(JapaneseWordFamiliarity.word_id, JapaneseWordFamiliarity.familiarity_score)
                               .where(JapaneseWordFamiliarity.user_id == user_id,
                                      JapaneseWordFamiliarity.word_id.in_(batch)))
        progress.update(rows.all())

    return [
        ParseJapaneseResponse(word_id=word_id, familiarity_score=progress.get(word_id, 0),
                              senses=senses)
        if word_id is not None else None
        for word_id, senses in zip(resolved_ids, resolved_senses, strict=True)
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
