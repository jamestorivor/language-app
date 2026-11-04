"""Reviewed expression patterns and a reusable token matcher.

Patterns use surface forms, dictionary forms and POS prefixes independently.
The registry is deliberately separate from grouping and dictionary lookup.
"""
from dataclasses import dataclass
from typing import Callable

from app.schemas import JapaneseTokenizedResponse as Token


@dataclass(frozen=True)
class TokenRule:
    surfaces: tuple[str, ...] = ()
    lemmas: tuple[str, ...] = ()
    pos: tuple[str, ...] = ()
    exclude_surfaces: tuple[str, ...] = ()

    def matches(self, token: Token) -> bool:
        return (
            (not self.surfaces or token.text in self.surfaces)
            and (not self.lemmas or token.dictionary_form in self.lemmas)
            and token.part_of_speech[:len(self.pos)] == self.pos
            and token.text not in self.exclude_surfaces
        )


@dataclass(frozen=True)
class ExpressionRule:
    pattern: tuple[TokenRule, ...]
    lookup_form: str
    source_entry_id: int
    # Continue through conjugation and supporting verbs from this pattern token.
    conjugation_head: int | None = None


def token(*surfaces: str, lemmas: tuple[str, ...] = (), pos: tuple[str, ...] = (), exclude: tuple[str, ...] = ()) -> TokenRule:
    return TokenRule(surfaces, lemmas, pos, exclude)


YOU = token("よう", pos=("形状詞", "助動詞語幹"))
COPULA_NI = token("に", lemmas=("だ",), pos=("助動詞",))
DOU_SHI_TE = (
    token("どう", pos=("副詞",)),
    token("し", lemmas=("する",), pos=("動詞",)),
    token("て", pos=("助詞", "接続助詞")),
)
KAMOSHIRE = (
    token("か", pos=("助詞",)),
    token("も", pos=("助詞",)),
    token(lemmas=("しれる", "知れる"), pos=("動詞",)),
)

EXPRESSION_RULES = (
    ExpressionRule((*KAMOSHIRE, token(lemmas=("ない",), pos=("助動詞",))), "かもしれない", 1002970, 2),
    ExpressionRule((*KAMOSHIRE, token("ませ", lemmas=("ます",), pos=("助動詞",)), token("ん", lemmas=("ぬ",), pos=("助動詞",))), "かもしれない", 1002970, 2),
    ExpressionRule((token("ふっ", pos=("副詞",)), token("と", pos=("助詞", "格助詞"))), "ふっと", 1632500),
    ExpressionRule((*DOU_SHI_TE, token("も", pos=("助詞",))), "どうしても", 1466950),
    ExpressionRule(DOU_SHI_TE, "どうして", 1466940),
    ExpressionRule((token("お", "御", pos=("接頭辞",)), token("土産", "みやげ", pos=("名詞",))), "お土産", 1002500),
    ExpressionRule((token("いつ"), token("の"), token("ま", "間"), token("に"), token("か")), "いつの間にか", 1188850),
    ExpressionRule((token("気", "き"), token("が", pos=("助詞",)), token(lemmas=("つく", "付く"), pos=("動詞",))), "気が付く", 1591050, 2),
    ExpressionRule((YOU, COPULA_NI, token(lemmas=("なる",), pos=("動詞",))), "ようになる", 1013130, 2),
    ExpressionRule((YOU, COPULA_NI), "ように", 1013110),
    ExpressionRule((YOU, token("な", lemmas=("だ",), pos=("助動詞",))), "ような", 2409180),
    ExpressionRule((YOU, token(lemmas=("だ",), pos=("助動詞",), exclude=("な", "に"))), "ようだ", 2409190, 0),
    ExpressionRule((YOU,), "ようだ", 2409190),
    ExpressionRule((token("ふう", "風", pos=("名詞",)), COPULA_NI), "風", 1499730),
    *(ExpressionRule((token(surface, pos=("名詞", "数詞")), token("つ", pos=("接尾辞", "名詞的", "助数詞"))), lookup, entry_id)
      for surface, lookup, entry_id in (
          ("ひと", "ひとつ", 1160820), ("一", "一つ", 1160820),
          ("ふた", "ふたつ", 1461160), ("二", "二つ", 1461160),
      )),
)


def match_reviewed_expression(tokens: list[Token], start: int, find_group_end: Callable[[list[Token], int], int], rules=EXPRESSION_RULES):
    matches = []
    for rule in rules:
        end = start + len(rule.pattern)
        if start < 0 or end > len(tokens):
            continue
        span = tokens[start:end]
        if not all(a.end_idx == b.start_idx for a, b in zip(span, span[1:])):
            continue
        if not all(spec.matches(item) for spec, item in zip(rule.pattern, span)):
            continue
        if rule.conjugation_head is not None:
            end = max(end, find_group_end(tokens, start + rule.conjugation_head))
        matches.append((end, rule.lookup_form, rule.source_entry_id))
    return max(matches, key=lambda match: match[0], default=None)
