from app.schemas import JapaneseTokenizedResponse, MajorPOS, PartOfSpeech, GroupToken
from app.data_access.japanese_vocab import get_word_details_batch
from app.services.japanese_vocab.expressions import match_reviewed_expression
from app.services.japanese_vocab.grammar import TE_EXTENSIONS, annotate_cross_group_grammar, annotate_grammar, match_grammar_construct
from app.schemas import GrammarMatch
from sqlalchemy.orm import Session

IGNORED_POS = {
    MajorPOS.PARTICLE,
    MajorPOS.AUXILIARY_VERB,
    MajorPOS.PREFIX,
    MajorPOS.SUFFIX,
    MajorPOS.SYMBOL,
    MajorPOS.SUPPLEMENTARY_SYMBOL,
    MajorPOS.WHITESPACE,
}

def adjacent(prev_token : JapaneseTokenizedResponse, curr_token : JapaneseTokenizedResponse):
    return prev_token.end_idx == curr_token.start_idx

def is_auxiliary(token : JapaneseTokenizedResponse):
    return token.part_of_speech[0] == MajorPOS.AUXILIARY_VERB

def is_negative_continuation(tokens : list[JapaneseTokenizedResponse], end : int):

    prev_token = tokens[end - 1]
    curr_token = tokens[end]

    if not adjacent(prev_token, curr_token):
        return False

    previous_pos = PartOfSpeech.from_sudachi(prev_token.part_of_speech)
    current_pos = PartOfSpeech.from_sudachi(curr_token.part_of_speech)

    # Handles 高く + ない and 食べたく + なかった.
    # Verb-negative auxiliaries are already handled by is_auxiliary().
    compatible_previous = (
        previous_pos.major_pos == MajorPOS.ADJECTIVE
        or (previous_pos.major_pos == MajorPOS.SUFFIX and previous_pos.subcategory_1 == "形容詞的")
        or (
            previous_pos.major_pos == MajorPOS.AUXILIARY_VERB
            and prev_token.dictionary_form == "たい"
        )
    )

    return (
        compatible_previous
        and previous_pos.conjugation_form.startswith("連用形")
        and current_pos.major_pos == MajorPOS.ADJECTIVE
        and current_pos.subcategory_1 == "非自立可能"
        and curr_token.dictionary_form == "ない"
    )

def is_te_form_ending(tokens: list[JapaneseTokenizedResponse], end: int) -> bool:
    if not 0 < end < len(tokens):
        return False

    previous = tokens[end - 1]
    particle = tokens[end]

    if not adjacent(previous, particle):
        return False

    previous_pos = PartOfSpeech.from_sudachi(previous.part_of_speech)
    particle_pos = PartOfSpeech.from_sudachi(particle.part_of_speech)

    return (
        previous_pos.major_pos in {
            MajorPOS.VERB,
            MajorPOS.ADJECTIVE,
            MajorPOS.AUXILIARY_VERB,
        }
        and previous_pos.conjugation_form.startswith("連用形")
        and particle.text in {"て", "で"}
        and particle_pos.major_pos == MajorPOS.PARTICLE
        and particle_pos.subcategory_1 == "接続助詞"
    )

def is_supporting_verb_bridge(tokens : list[JapaneseTokenizedResponse], end : int):
    # Check the longer construction before accepting a standalone て/で ending.
    if not is_te_form_ending(tokens, end) or end + 1 >= len(tokens):
        return False

    particle = tokens[end]
    following = tokens[end + 1]
    following_pos = PartOfSpeech.from_sudachi(following.part_of_speech)

    return (
        adjacent(particle, following)
        and following_pos.major_pos == MajorPOS.VERB
        and following_pos.subcategory_1 == "非自立可能"
        and following.dictionary_form in TE_EXTENSIONS
    )

def find_group_end(tokens : list[JapaneseTokenizedResponse], start_index : int):
    end = start_index + 1

    while end < len(tokens):
        if not adjacent(tokens[end - 1], tokens[end]):
            break

        if is_auxiliary(tokens[end]):
            end += 1
        elif is_negative_continuation(tokens, end):
            end += 1
        elif is_supporting_verb_bridge(tokens, end):
            end += 2  # Consume both て/で and the supporting verb
        elif is_te_form_ending(tokens, end):
            end += 1
            break  # Include the ending, leaving the following word independent.
        else:
            break

    return end


def person_name_end(tokens: list[JapaneseTokenizedResponse], start: int) -> int | None:
    """Use person-name POS or an honorific attached to a proper noun as evidence."""
    token = tokens[start]
    if token.part_of_speech[:2] != (MajorPOS.NOUN, "固有名詞"):
        return None
    honorifics = {"さん", "ちゃん", "くん", "君", "様", "さま"}
    end = start + 1
    following_honorific = (end < len(tokens) and adjacent(token, tokens[end])
        and tokens[end].part_of_speech[0] == MajorPOS.SUFFIX
        and tokens[end].text in honorifics)
    embedded_honorific = any(token.text.endswith(suffix) and len(token.text) > len(suffix)
                             for suffix in honorifics)
    # A bare one-character word such as 金 is often tagged as a surname by
    # Sudachi even when the ordinary dictionary meaning is intended.
    person_tag = token.part_of_speech[2] == "人名" and len(token.text) > 1
    if not person_tag and not following_honorific and not embedded_honorific:
        return None
    return end + 1 if following_honorific else end


def productive_suffix_end(tokens: list[JapaneseTokenizedResponse], start: int) -> int | None:
    """Attach a few productive suffixes while retaining the head word identity."""
    if start + 1 >= len(tokens):
        return None
    head, suffix = tokens[start:start + 2]
    if not adjacent(head, suffix) or suffix.part_of_speech[0] != MajorPOS.SUFFIX:
        return None
    if (head.part_of_speech[0] in {MajorPOS.NOUN, MajorPOS.PRONOUN} and suffix.dictionary_form in {"たち", "達"}):
        return start + 2
    if (head.part_of_speech[0] == MajorPOS.VERB
        and head.part_of_speech[5].startswith("連用形")
        and suffix.dictionary_form in {"方", "かた", "やすい", "易い", "にくい", "難い"}):
        return find_group_end(tokens, start + 1)
    return None

def join_tokens(original_text:str, tokens : list[JapaneseTokenizedResponse], start_idx:int, group_length:int):
    VERB_HEAD_OFFSET = 1
    start_token = tokens[start_idx]
    end_token_idx = start_idx + group_length - VERB_HEAD_OFFSET
    end_token = tokens[end_token_idx]


    return GroupToken(
        text= original_text[start_token.start_idx: end_token.end_idx],
        lookup_form=start_token.dictionary_form,
        start_idx=start_token.start_idx,
        end_idx=end_token.end_idx,
        tokens=tokens[start_idx : end_token_idx + 1],
    )


def match_expression(tokens: list[JapaneseTokenizedResponse], start: int):
    return match_reviewed_expression(tokens, start, find_group_end)


# Sudachi analyses kana つまらない as 詰まる + ない even when it is the
# common adjective "boring". Explicitly written 詰まらない remains a verb;
# a nearby subject referring to something that clogs is also evidence for it.
CLOGGABLE_SUBJECTS = frozenset({
    "管", "配管", "水道管", "パイプ", "排水管", "排水口", "排水溝", "穴", "鼻",
    "鼻孔", "喉", "血管", "気管", "ノズル", "トイレ", "便器", "ホース", "フィルター",
})


def is_lexical_tsumaranai(groups: list[GroupToken], index: int) -> bool:
    group = groups[index]
    if not (group.text.startswith("つまら") and group.lookup_form == "つまる"
            and len(group.tokens) >= 2 and group.tokens[1].dictionary_form == "ない"):
        return False
    # Only look within the current clause and inspect the nearest subject.
    preceding = groups[max(0, index - 4):index]
    for i in range(len(preceding) - 1, 0, -1):
        if preceding[i].text in {"。", "、", "！", "？", "!", "?", ","}:
            break
        if preceding[i].text in {"が", "は", "も"}:
            return preceding[i - 1].text not in CLOGGABLE_SUBJECTS
    return True


def regroup_tokens(original_text : str, tokens : list[JapaneseTokenizedResponse], dictionary_matches=None) -> list[GroupToken]:
    curr_idx = 0
    token_list_length = len(tokens)
    output_token_list = []

    while curr_idx < token_list_length:
        curr_token = tokens[curr_idx]
        major_part_of_speech = curr_token.part_of_speech[0]
        grammar_construct = match_grammar_construct(tokens, curr_idx)
        expression = match_expression(tokens, curr_idx)
        name_end = person_name_end(tokens, curr_idx)
        if name_end is not None:
            group = join_tokens(original_text, tokens, curr_idx, name_end - curr_idx)
            group._grammar_only = True
            group.grammar.append(GrammarMatch(id="person_name", text=group.text,
                meaning="A person's name, sometimes followed by an honorific.",
                start_idx=group.start_idx, end_idx=group.end_idx))
            output_token_list.append(group)
            curr_idx = name_end
        elif grammar_construct and (not expression or grammar_construct[0] > expression[0]):
            group_end, grammar_id, meaning = grammar_construct
            group = join_tokens(original_text, tokens, curr_idx, group_end - curr_idx)
            group._grammar_only = True
            group.grammar.append(GrammarMatch(id=grammar_id, text=group.text, meaning=meaning,
                                              start_idx=group.start_idx, end_idx=group.end_idx))
            output_token_list.append(group)
            curr_idx = group_end
        elif expression:
            group_end, lookup_form, source_entry_id = expression
            new_token = join_tokens(original_text, tokens, curr_idx, group_end - curr_idx)
            new_token.lookup_form = lookup_form
            new_token.source_entry_id = source_entry_id
            output_token_list.append(new_token)
            curr_idx = group_end
        elif dictionary_matches and curr_idx in dictionary_matches:
            match = max(dictionary_matches[curr_idx], key=lambda item: item.end)
            group_end = match.end
            if match.conjugation_head is not None:
                group_end = max(group_end, find_group_end(tokens, match.conjugation_head))
            new_token = join_tokens(original_text, tokens, curr_idx, group_end - curr_idx)
            new_token.lookup_form = match.lookup_form
            new_token.source_entry_id = match.source_entry_id
            output_token_list.append(new_token)
            curr_idx = group_end
        elif (suffix_end := productive_suffix_end(tokens, curr_idx)) is not None:
            output_token_list.append(join_tokens(original_text, tokens, curr_idx, suffix_end - curr_idx))
            curr_idx = suffix_end
        elif major_part_of_speech in {MajorPOS.VERB, MajorPOS.ADJECTIVE}:
            group_end = find_group_end(tokens,curr_idx)
            group_length = group_end - curr_idx
            new_verb_token = join_tokens(original_text,tokens, curr_idx, group_length)
            output_token_list.append(new_verb_token)
            curr_idx += group_length
        else:
            output_token_list.append(
                GroupToken(
                    text=curr_token.text,
                    lookup_form=curr_token.dictionary_form,
                    start_idx=curr_token.start_idx,
                    end_idx=curr_token.end_idx,
                    tokens=[curr_token],
                )
            )
            curr_idx += 1
    for index, group in enumerate(output_token_list):
        group._followed_by_pause = original_text[group.end_idx:group.end_idx + 1] in {"、", "，", ","}
        lexical_tsumaranai = is_lexical_tsumaranai(output_token_list, index)
        if lexical_tsumaranai:
            group.lookup_form = "つまらない"
            group.source_entry_id = 1008190
        annotations = annotate_grammar(group)
        if lexical_tsumaranai:
            annotations = [annotation for annotation in annotations if annotation.id != "negative"]
        group.grammar.extend(annotations)
    annotate_cross_group_grammar(output_token_list, tokens, original_text)
    return output_token_list

def get_display_status(token : GroupToken) :
    # Update in the future if neccessary 
    # Current -> If word does not exist in db, do set display to false
    if token._grammar_only:
        return True
    if not token.word_id:
        return False

    # A recognized expression can start with a normally ignored particle.
    if token.source_entry_id is not None:
        return True

    # Need to update logic for familiarity, set to 6 to allow all scores for now
    # THRESHOLD_FAMILIARITY_SCORE = 6
    # FAMILIAR_ENOUGH = token.familiarity_score >= THRESHOLD_FAMILIARITY_SCORE

    major_part_of_speech = token.tokens[0].part_of_speech[0]
    if major_part_of_speech in IGNORED_POS:
        return False
    
    # if FAMILIAR_ENOUGH:
    #     return False
    return True

def add_db_data_to_tokens(db : Session, group_tokens : list[GroupToken], user_id : int) -> list[GroupToken] :
    enriched_tokens = []
    details = get_word_details_batch(db, group_tokens, user_id)
    for token, db_data in zip(group_tokens, details, strict=True):

        if db_data and not token._grammar_only:
            token.word_id=db_data.word_id
            token.familiarity_score=db_data.familiarity_score
            token.senses=db_data.senses

        token.display = get_display_status(token)
        enriched_tokens.append(token)
    return enriched_tokens

