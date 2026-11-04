"""Small reviewed grammar annotations over the original Sudachi tokens."""
from app.schemas import GrammarMatch, GroupToken, JapaneseTokenizedResponse, MajorPOS


TE_EXTENSIONS = {
    "いる": ("te_iru", "An ongoing action or resulting state."),
    "居る": ("te_iru", "An ongoing action or resulting state."),
    "みる": ("te_miru", "Try doing something."),
    "見る": ("te_miru", "Try doing something."),
    "おく": ("te_oku", "Do something in preparation, or leave it in a state."),
    "置く": ("te_oku", "Do something in preparation, or leave it in a state."),
    "しまう": ("te_shimau", "Complete an action, sometimes with regret."),
    "仕舞う": ("te_shimau", "Complete an action, sometimes with regret."),
    "くる": ("te_kuru", "An action toward the speaker, or a change up to now."),
    "来る": ("te_kuru", "An action toward the speaker, or a change up to now."),
    "いく": ("te_iku", "An action away from the speaker, or a change continuing onward."),
    "行く": ("te_iku", "An action away from the speaker, or a change continuing onward."),
    "ゆく": ("te_iku", "An action away from the speaker, or a change continuing onward."),
    "もらう": ("te_morau", "Have someone do something for you."),
    "貰う": ("te_morau", "Have someone do something for you."),
    "あげる": ("te_ageru", "Do something for someone."),
    "上げる": ("te_ageru", "Do something for someone."),
    "くれる": ("te_kureru", "Someone does something for you or your group."),
    "呉れる": ("te_kureru", "Someone does something for you or your group."),
    "くださる": ("te_kudasaru", "A respectful request or action done for the speaker."),
    "下さる": ("te_kudasaru", "A respectful request or action done for the speaker."),
    "やる": ("te_yaru", "Do something for someone, in informal usage."),
    "遣る": ("te_yaru", "Do something for someone, in informal usage."),
}

EXPRESSION_GRAMMAR = {
    "ようになる": ("you_ni_naru", "Come to; reach the point where a state or habit changes."),
    "ように": ("you_ni", "Like; in the manner of; so that, depending on context."),
    "ような": ("you_na", "Like; similar to."),
    "ようだ": ("you_da", "Seems; appears; is like."),
    "かもしれない": ("kamoshirenai", "Might; perhaps."),
}


def annotate_grammar(group: GroupToken) -> list[GrammarMatch]:
    annotations = []
    if group.source_entry_id is not None and group.lookup_form in EXPRESSION_GRAMMAR:
        grammar_id, meaning = EXPRESSION_GRAMMAR[group.lookup_form]
        annotations.append(GrammarMatch(id=grammar_id, text=group.text, meaning=meaning, start_idx=group.start_idx, end_idx=group.end_idx))
    tokens = group.tokens
    for index in range(1, len(tokens)):
        particle, verb = tokens[index - 1:index + 1]
        if (particle.text not in {"て", "で"} or particle.part_of_speech[:2] != (MajorPOS.PARTICLE, "接続助詞")
            or particle.end_idx != verb.start_idx or verb.part_of_speech[:2] != (MajorPOS.VERB, "非自立可能")
            or verb.dictionary_form not in TE_EXTENSIONS):
            continue
        grammar_id, meaning = TE_EXTENSIONS[verb.dictionary_form]
        end = index + 1
        while end < len(tokens) and tokens[end - 1].end_idx == tokens[end].start_idx and tokens[end].part_of_speech[0] == MajorPOS.AUXILIARY_VERB:
            end += 1
        end_idx = tokens[end - 1].end_idx
        start_idx = particle.start_idx
        annotations.append(GrammarMatch(id=grammar_id, text=group.text[start_idx - group.start_idx:end_idx - group.start_idx], meaning=meaning, start_idx=start_idx, end_idx=end_idx))
    return annotations


def find_no_hou_ga(tokens: list[JapaneseTokenizedResponse]) -> list[tuple[int, int, int]]:
    """Find noun + の + ほう/方 + が; return indices of の, ほう and が."""
    matches = []
    for start in range(len(tokens) - 3):
        noun, no, hou, ga = tokens[start:start + 4]
        if (
            noun.part_of_speech[0] in {MajorPOS.NOUN, MajorPOS.PRONOUN}
            and no.text == "の" and no.part_of_speech[0] == MajorPOS.PARTICLE
            and hou.text in {"ほう", "方"} and hou.part_of_speech[0] == MajorPOS.NOUN
            and hou.katakana_reading == "ホウ"
            and ga.text == "が" and ga.part_of_speech[0] == MajorPOS.PARTICLE
            and all(a.end_idx == b.start_idx for a, b in zip((noun, no, hou), (no, hou, ga)))
        ):
            matches.append((start + 1, start + 2, start + 3))
    return matches


def annotate_cross_group_grammar(groups: list[GroupToken], tokens: list[JapaneseTokenizedResponse], original_text: str) -> None:
    for no_index, hou_index, ga_index in find_no_hou_ga(tokens):
        no, hou, ga = tokens[no_index], tokens[hou_index], tokens[ga_index]
        group = next((g for g in groups if g.start_idx <= hou.start_idx and hou.end_idx <= g.end_idx), None)
        if group is None:
            continue
        group.grammar.append(GrammarMatch(
            id="no_hou_ga",
            text=original_text[no.start_idx:ga.end_idx],
            meaning="Can mark one side of a comparison: 'the ... one', 'rather', or 'more'. 方 can also refer to a direction depending on context.",
            start_idx=no.start_idx,
            end_idx=ga.end_idx,
        ))
