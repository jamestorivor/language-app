from dataclasses import dataclass


@dataclass(frozen=True)
class RankingCandidate:
    word_id: int
    # POS tags for applicable senses, using JMdict's expanded descriptions.
    parts_of_speech: frozenset[str]
    # Priority tags on the spelling or reading that matched the lookup.
    priorities: frozenset[str]


COMMON_PRIORITIES = frozenset({"ichi1", "news1", "spec1", "gai1"})


def _pos_matches(sudachi_pos: str, jmdict_pos: str) -> bool:
    """Compare broad categories; the two dictionaries use different labels."""
    pos = jmdict_pos.casefold()
    if sudachi_pos == "名詞":
        return pos.startswith("noun") or pos in {"n", "n-adv", "n-t"}
    if sudachi_pos == "動詞":
        return "verb" in pos or pos.startswith(("v1", "v2", "v4", "v5", "vk", "vs", "vz"))
    if sudachi_pos == "形容詞":
        return pos.startswith("adjective (keiyoushi)") or pos in {"adj-i", "adj-ix"}
    if sudachi_pos == "形状詞":
        return pos.startswith("adjectival nouns") or pos == "adj-na"
    if sudachi_pos == "副詞":
        return pos.startswith("adverb") or pos in {"adv", "adv-to"}
    if sudachi_pos == "連体詞":
        return pos.startswith("pre-noun adjectival") or pos == "adj-pn"
    if sudachi_pos == "代名詞":
        return pos == "pronoun" or pos == "pn"
    return False


def rank_by_pos_and_frequency(
    candidates: list[RankingCandidate], sudachi_pos: str, conjugation_type: str = ""
) -> list[RankingCandidate]:
    """Rank candidates by POS, verb class, and common priority tags.

    Input order breaks ties. Unknown Sudachi categories and missing JMdict POS
    are neutral rather than being treated as incompatible.
    """
    supported_pos = {"名詞", "動詞", "形容詞", "形状詞", "副詞", "連体詞", "代名詞"}
    sudachi_verb_class = None
    if sudachi_pos == "動詞":
        if conjugation_type.startswith(("上一段", "下一段")):
            sudachi_verb_class = "ichidan"
        elif conjugation_type.startswith("五段"):
            sudachi_verb_class = "godan"

    def verb_classes(parts_of_speech: frozenset[str]) -> set[str]:
        classes = set()
        for tag in parts_of_speech:
            pos = tag.casefold()
            if pos.startswith("ichidan verb") or pos.startswith("v1"):
                classes.add("ichidan")
            elif pos.startswith("godan verb") or pos.startswith("v5"):
                classes.add("godan")
        return classes

    def score(candidate: RankingCandidate) -> int:
        pos_score = 0
        if sudachi_pos in supported_pos and candidate.parts_of_speech:
            pos_score = 10 if any(
                _pos_matches(sudachi_pos, pos) for pos in candidate.parts_of_speech
            ) else -5
        class_score = 0
        classes = verb_classes(candidate.parts_of_speech)
        if sudachi_verb_class and classes:
            class_score = 4 if sudachi_verb_class in classes else -4
        common_tags = candidate.priorities & COMMON_PRIORITIES
        # Multiple priority markers provide a modest tie-breaker;
        # never let commonness outweigh a compatible POS or verb class.
        frequency_score = min(len(common_tags), 2)
        return pos_score + class_score + frequency_score

    return sorted(candidates, key=score, reverse=True)
