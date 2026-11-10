"""English tokenization and dictionary lookup."""
from collections import defaultdict
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.import_english_dictionary import lookup_key
from app.db.models.english_vocab import EnglishDictionary, EnglishWordFamiliarity
from app.schemas import GroupToken, JapaneseTokenizedResponse

MAX_PHRASE_TOKENS = 4
QUERY_BATCH_SIZE = 500


@lru_cache(maxsize=1)
def english_pipeline():
    import spacy
    return spacy.load("en_core_web_sm", disable=["ner", "parser"])


def _token(text: str, lemma: str, pos: str, start: int, end: int) -> JapaneseTokenizedResponse:
    return JapaneseTokenizedResponse(text=text, dictionary_form=lemma, katakana_reading="",
                                     start_idx=start, end_idx=end,
                                     part_of_speech=(pos, "", "", "", "", ""))


def _dictionary_senses(meaning: str) -> list[dict]:
    # EJDict uses a spaced slash for alternatives; keep its other annotations intact.
    return [{"glosses": [part.strip()]} for line in meaning.splitlines()
            for part in line.split(" / ") if part.strip()]


def parse_english_text(session: Session, text: str, user_id: int) -> list[GroupToken]:
    doc = english_pipeline()(text)
    words = [token for token in doc if not token.is_space]
    candidates: dict[int, list[tuple[int, str, str]]] = defaultdict(list)
    keys = set()
    for start, first in enumerate(words):
        if first.is_punct or first.is_space:
            continue
        for end in range(start + 1, min(len(words), start + MAX_PHRASE_TOKENS) + 1):
            span = words[start:end]
            if span[-1].is_punct or any("\n" in text[a.idx + len(a.text):b.idx] for a, b in zip(span, span[1:])):
                break
            surface = text[first.idx:span[-1].idx + len(span[-1].text)]
            lemma_parts = []
            for idx, token in enumerate(span):
                if idx:
                    previous = span[idx - 1]
                    lemma_parts.append(text[previous.idx + len(previous.text):token.idx])
                lemma_parts.append(token.lemma_ or token.text)
            lemma = "".join(lemma_parts)
            candidates[start].append((end, surface, lemma))
            keys.update((lookup_key(surface), lookup_key(lemma)))

    by_key: dict[str, list[EnglishDictionary]] = defaultdict(list)
    all_keys = list(keys)
    for start in range(0, len(all_keys), QUERY_BATCH_SIZE):
        for entry in session.scalars(select(EnglishDictionary).where(
            EnglishDictionary.lookup_key.in_(all_keys[start:start + QUERY_BATCH_SIZE])
        )):
            by_key[entry.lookup_key].append(entry)

    def choose(form: str):
        matches = by_key.get(lookup_key(form), [])
        return min(matches, key=lambda entry: (entry.headword != form, entry.headword != form.casefold(), entry.word_id), default=None)

    groups: list[GroupToken] = []
    position = 0
    index = 0
    while index < len(words):
        first = words[index]
        if position < first.idx:
            gap = text[position:first.idx]
            groups.append(GroupToken(text=gap, lookup_form=gap, start_idx=position, end_idx=first.idx,
                                     tokens=[_token(gap, gap, "SPACE", position, first.idx)], display=False))
        selected = None
        for end, surface, lemma in reversed(candidates.get(index, [])):
            entry = choose(lemma) or choose(surface)
            if entry is not None:
                selected = (end, entry)
                break
        end, entry = selected or (index + 1, None)
        span = words[index:end]
        end_pos = span[-1].idx + len(span[-1].text)
        token_data = [_token(t.text, t.lemma_ or t.text, t.pos_, t.idx, t.idx + len(t.text)) for t in span]
        groups.append(GroupToken(text=text[first.idx:end_pos], lookup_form=entry.headword if entry else (first.lemma_ or first.text),
                                 start_idx=first.idx, end_idx=end_pos, tokens=token_data,
                                 word_id=entry.word_id if entry else None,
                                 senses=_dictionary_senses(entry.meaning) if entry else None,
                                 familiarity_score=0 if entry else None, display=entry is not None))
        position = end_pos
        index = end
    if position < len(text):
        gap = text[position:]
        groups.append(GroupToken(text=gap, lookup_form=gap, start_idx=position, end_idx=len(text),
                                 tokens=[_token(gap, gap, "SPACE", position, len(text))], display=False))

    ids = {group.word_id for group in groups if group.word_id is not None}
    scores = {}
    id_list = list(ids)
    for start in range(0, len(id_list), QUERY_BATCH_SIZE):
        scores.update(session.execute(select(EnglishWordFamiliarity.word_id, EnglishWordFamiliarity.familiarity_score).where(
            EnglishWordFamiliarity.user_id == user_id,
            EnglishWordFamiliarity.word_id.in_(id_list[start:start + QUERY_BATCH_SIZE]),
        )).all())
    for group in groups:
        if group.word_id is not None:
            group.familiarity_score = scores.get(group.word_id, 0)
    return groups
