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


def match_grammar_construct(tokens: list[JapaneseTokenizedResponse], start: int):
    """Recognize restricted function-word spans without choosing a homophone."""
    def matches(specs):
        span = tokens[start:start + len(specs)]
        return (len(span) == len(specs)
                and all(a.end_idx == b.start_idx for a, b in zip(span, span[1:]))
                and all(t.text in surfaces and t.part_of_speech[0] == pos
                        for t, (surfaces, pos) in zip(span, specs)))

    p = MajorPOS.PARTICLE
    patterns = (
        ((({"と"}, p), ({"いう", "言う"}, MajorPOS.VERB), ({"の"}, p), ({"は"}, p)),
         "to_iu_no_wa", "Introduces a topic or explanation: ‘as for what is called ...’."),
        ((({"と"}, p), ({"か"}, p), ({"で"}, MajorPOS.AUXILIARY_VERB)),
         "toka_de", "Gives an example or approximate circumstance, such as ‘with ... or something’."),
        ((({"と"}, p), ({"か"}, p), ({"で"}, p)),
         "toka_de", "Gives an example or approximate circumstance, such as ‘with ... or something’."),
        ((({"で"}, p), ({"は"}, p)),
         "dewa", "Combines で with the topic or contrast marker は; it can also mean ‘well then’."),
        ((({"と"}, p), ({"は"}, p)),
         "towa", "Combines と with the topic or contrast marker は; often introduces or contrasts a topic."),
    )
    for specs, grammar_id, meaning in patterns:
        if matches(specs):
            return start + len(specs), grammar_id, meaning
    token = tokens[start]
    if token.text == "ないし" and token.part_of_speech[0] == MajorPOS.CONJUNCTION:
        return start + 1, "naishi", "‘Or’ or ‘to’, depending on context."
    if token.text in {"で", "て"} and token.part_of_speech[0] == p:
        return start + 1, "particle_" + token.text, (
            "A particle marking a place, means, cause or connection, depending on context." if token.text == "で"
            else "A connective particle linking clauses or actions."
        )
    if token.text in {"ため", "為"} and token.part_of_speech[0] == MajorPOS.NOUN:
        previous = tokens[start - 1] if start else None
        following = tokens[start + 1] if start + 1 < len(tokens) else None
        if ((previous and previous.end_idx == token.start_idx and (previous.text in {"の", "その"}
             or previous.part_of_speech[0] in {MajorPOS.VERB, MajorPOS.AUXILIARY_VERB}))
            or (following and token.end_idx == following.start_idx and following.text == "に")):
            return start + 1, "tame", "Can express purpose or benefit (‘for’), or a reason (‘because of’), depending on context."
    if token.text in {"ところ", "所"} and token.part_of_speech[0] == MajorPOS.NOUN and start:
        previous = tokens[start - 1]
        if previous.end_idx == token.start_idx and previous.part_of_speech[0] in {MajorPOS.VERB, MajorPOS.AUXILIARY_VERB}:
            return start + 1, "tokoro", "After a verb, can refer to the point or stage of an action, or a place, depending on context."
    return None


def annotate_grammar(group: GroupToken) -> list[GrammarMatch]:
    annotations = []
    if group.source_entry_id is not None and group.lookup_form in EXPRESSION_GRAMMAR:
        grammar_id, meaning = EXPRESSION_GRAMMAR[group.lookup_form]
        annotations.append(GrammarMatch(id=grammar_id, text=group.text, meaning=meaning, start_idx=group.start_idx, end_idx=group.end_idx))
    tokens = group.tokens
    # The lookup form is the dictionary head, while these annotations describe
    # what the inflected surface says. Do not mistake lexical ない in a reviewed
    # expression (such as かもしれない) for negation of its whole meaning.
    if group.lookup_form not in EXPRESSION_GRAMMAR and len(tokens) > 1:
        desire = any(t.dictionary_form == "たい" and t.part_of_speech[0] == MajorPOS.AUXILIARY_VERB for t in tokens[1:])
        negative = any(
            t.dictionary_form in {"ない", "ぬ", "ん", "へん"}
            and t.part_of_speech[0] in {MajorPOS.AUXILIARY_VERB, MajorPOS.ADJECTIVE}
            for t in tokens[1:]
        )
        if desire or negative:
            grammar_id = "negative_desire" if desire and negative else "negative" if negative else "desire"
            meaning = ("Does not want to do the action." if desire and negative else
                       "Negative form: the action or state is negated." if negative else
                       "Wants to do the action.")
            annotations.append(GrammarMatch(id=grammar_id, text=group.text, meaning=meaning,
                                            start_idx=group.start_idx, end_idx=group.end_idx))
        suffix = tokens[1]
        if group.source_entry_id is None and suffix.part_of_speech[0] == MajorPOS.SUFFIX:
            suffix_meanings = {
                "たち": ("plural", "Plural: the person or people and their group."),
                "達": ("plural", "Plural: the person or people and their group."),
                "方": ("way_of", "The way or method of doing the action."),
                "かた": ("way_of", "The way or method of doing the action."),
                "やすい": ("easy_to", "Easy to do the action."),
                "易い": ("easy_to", "Easy to do the action."),
                "にくい": ("hard_to", "Difficult to do the action."),
                "難い": ("hard_to", "Difficult to do the action."),
            }
            if suffix.dictionary_form in suffix_meanings:
                grammar_id, meaning = suffix_meanings[suffix.dictionary_form]
                annotations.append(GrammarMatch(id=grammar_id, text=group.text, meaning=meaning,
                                                start_idx=group.start_idx, end_idx=group.end_idx))
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
    if (len(tokens) > 1 and tokens[-1].text in {"て", "で"}
        and tokens[-1].part_of_speech[:2] == (MajorPOS.PARTICLE, "接続助詞")
        and not any(item.id.startswith("te_") for item in annotations)):
        ending = tokens[-1]
        annotations.append(GrammarMatch(id="te_form", text=ending.text,
            meaning="Connects the preceding action or state to what follows.",
            start_idx=ending.start_idx, end_idx=ending.end_idx))
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
    # Keep する as the independently rated head (including any ている etc.)
    # while describing the preceding object marker as part of the construction.
    for index in range(len(tokens) - 2):
        particle, verb, te = tokens[index:index + 3]
        if (particle.text == "を" and particle.part_of_speech[0] == MajorPOS.PARTICLE
            and verb.text == "し" and verb.dictionary_form == "する" and verb.part_of_speech[0] == MajorPOS.VERB
            and te.text == "て" and te.part_of_speech[:2] == (MajorPOS.PARTICLE, "接続助詞")
            and particle.end_idx == verb.start_idx and verb.end_idx == te.start_idx):
            group = next((g for g in groups if g.start_idx <= verb.start_idx < g.end_idx), None)
            if group is not None:
                group.grammar.append(GrammarMatch(id="wo_shite", text=original_text[particle.start_idx:te.end_idx],
                    meaning="The object marker を followed by して, the connective form of する (‘do’).",
                    start_idx=particle.start_idx, end_idx=te.end_idx))
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
