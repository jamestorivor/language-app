"""Find conservative multi-token JMdict matches with batched queries."""
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseReading, JapaneseSpelling
from app.schemas import JapaneseTokenizedResponse, MajorPOS
from app.services.japanese_vocab.grammar import find_no_hou_ga

MAX_TOKENS = 5
MAX_CHARACTERS = 30
QUERY_BATCH_SIZE = 500


@dataclass(frozen=True)
class DictionaryExpression:
    end: int
    lookup_form: str
    source_entry_id: int
    conjugation_head: int | None = None


def _is_expression(senses) -> bool:
    return any(
        pos.casefold().startswith("expressions (phrases") or pos == "exp"
        for sense in senses for pos in (sense.get("pos") or [])
    )


def find_dictionary_expressions(session: Session, tokens: list[JapaneseTokenizedResponse]):
    # Keep only boundaries that cannot cross punctuation, whitespace or gaps.
    forms = defaultdict(list)
    # Keep the grammar marker and 方 independently selectable, even if a
    # longer JMdict expression happens to match across these token boundaries.
    protected = {index for match in find_no_hou_ga(tokens) for index in match}
    for start, first in enumerate(tokens):
        if first.part_of_speech[0] in {MajorPOS.WHITESPACE, MajorPOS.SYMBOL, MajorPOS.SUPPLEMENTARY_SYMBOL}:
            continue
        for end in range(start + 2, min(len(tokens), start + MAX_TOKENS) + 1):
            span = tokens[start:end]
            last = span[-1]
            if any(index in protected for index in range(start, end)):
                break
            if (any(t.part_of_speech[0] in {MajorPOS.WHITESPACE, MajorPOS.SYMBOL, MajorPOS.SUPPLEMENTARY_SYMBOL} for t in span)
                or any(a.end_idx != b.start_idx for a, b in zip(span, span[1:]))):
                break
            surface = "".join(t.text for t in span)
            if len(surface) > MAX_CHARACTERS:
                break
            prefix_noun = (len(span) == 2 and first.text in {"お", "ご", "御"}
                           and first.part_of_speech[0] == MajorPOS.PREFIX
                           and last.part_of_speech[0] == MajorPOS.NOUN)
            forms[surface].append((start, end, prefix_noun, None))
            if last.part_of_speech[0] == MajorPOS.VERB and last.text != last.dictionary_form:
                base = "".join(t.text for t in span[:-1]) + last.dictionary_form
                if len(base) <= MAX_CHARACTERS:
                    forms[base].append((start, end, False, end - 1))

    # Fetch full entries once per batch; ambiguity is not resolved by row order.
    matches = defaultdict(dict)
    keys = list(forms)
    for offset in range(0, len(keys), QUERY_BATCH_SIZE):
        batch = keys[offset:offset + QUERY_BATCH_SIZE]
        for model, column in ((JapaneseSpelling, JapaneseSpelling.spelling), (JapaneseReading, JapaneseReading.reading)):
            rows = session.execute(select(column, JapaneseDictionary).join(model, model.word_id == JapaneseDictionary.word_id).where(column.in_(batch)))
            for form, entry in rows:
                matches[form][entry.source_entry_id] = entry

    output = defaultdict(list)
    for form, spans in forms.items():
        for start, end, prefix_noun, head in spans:
            eligible = [entry for entry in matches[form].values() if prefix_noun or _is_expression(entry.senses)]
            # A dictionary form with multiple entries needs disambiguation;
            # leave it ungrouped instead of selecting an arbitrary homophone.
            if len(eligible) == 1:
                output[start].append(DictionaryExpression(end, form, eligible[0].source_entry_id, head))
    return dict(output)
