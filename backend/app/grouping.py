from app.schemas import JapaneseTokenizedResponse, MajorPOS, PartOfSpeech, TokenGroup

SUPPORTING_VERBS = {"いる", "しまう", "おく"}

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

def is_supporting_verb_bridge(tokens : list[JapaneseTokenizedResponse], end : int):
    # Requires a previous token, a particle, and a following verb.
    if not 0 < end < len(tokens) - 1:
        return False

    previous = tokens[end - 1]
    particle = tokens[end]
    following = tokens[end + 1]

    if not (
        adjacent(previous, particle)
        and adjacent(particle, following)
    ):
        return False

    previous_pos = PartOfSpeech.from_sudachi(previous.part_of_speech)
    particle_pos = PartOfSpeech.from_sudachi(particle.part_of_speech)
    following_pos = PartOfSpeech.from_sudachi(following.part_of_speech)

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
        and following_pos.major_pos == MajorPOS.VERB
        and following_pos.subcategory_1 == "非自立可能"
        and following.dictionary_form in SUPPORTING_VERBS
    )

def is_kamoshirenai_bridge(
    tokens: list[JapaneseTokenizedResponse],
    end: int,
) -> bool:
    # Need か + も + しれ and at least one negative-ending token.
    if end < 0 or end + 3 >= len(tokens):
        return False

    ka, mo, shire = tokens[end:end + 3]

    if not (
        ka.text == "か"
        and ka.part_of_speech[0] == MajorPOS.PARTICLE
        and mo.text == "も"
        and mo.part_of_speech[0] == MajorPOS.PARTICLE
        and shire.dictionary_form in {"しれる", "知れる"}
        and shire.part_of_speech[0] == MajorPOS.VERB
    ):
        return False

    # Require a negative continuation before accepting the bridge.
    tail = tokens[end + 3:end + 5]

    if (
        is_auxiliary(tail[0])
        and tail[0].dictionary_form == "ない"
    ):
        matched_end = end + 4
    elif (
        len(tail) == 2
        and all(is_auxiliary(token) for token in tail)
        and tail[0].text == "ませ"
        and tail[0].dictionary_form == "ます"
        and tail[1].text == "ん"
        and tail[1].dictionary_form == "ぬ"
    ):
        matched_end = end + 5
    else:
        return False

    # Check the expression itself; find_group_end checks its previous boundary.
    return all(
        adjacent(tokens[i - 1], tokens[i])
        for i in range(end + 1, matched_end)
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
        elif is_kamoshirenai_bridge(tokens, end):
            end += 3  # Consume か + も + しれ
        else:
            break

    return end

def join_tokens(original_text:str, tokens : list[JapaneseTokenizedResponse], start_idx:int, group_length:int):
    VERB_HEAD_OFFSET = 1
    start_token = tokens[start_idx]
    end_token_idx = start_idx + group_length - VERB_HEAD_OFFSET
    end_token = tokens[end_token_idx]


    return TokenGroup(
        text= original_text[start_token.start_idx: end_token.end_idx],
        lookup_form=start_token.dictionary_form,
        start_idx=start_token.start_idx,
        end_idx=end_token.end_idx,
        tokens=tokens[start_idx : end_token_idx + 1]
    )


def regroup_tokens(original_text : str, tokens : list[JapaneseTokenizedResponse]):
    curr_idx = 0
    token_list_length = len(tokens)
    output_token_list = []

    while curr_idx < token_list_length:
        curr_token = tokens[curr_idx]
        
        major_part_of_speech = curr_token.part_of_speech[0]
        if is_kamoshirenai_bridge(tokens, curr_idx):
            # Start at か even after a noun, particle, or sentence boundary.
            # Continue from しれ to consume its auxiliaries, including past forms.
            group_end = find_group_end(tokens, curr_idx + 2)
            new_token = join_tokens(
                original_text, tokens, curr_idx, group_end - curr_idx
            )
            new_token.lookup_form = "かもしれない"
            output_token_list.append(new_token)
            curr_idx = group_end
        elif major_part_of_speech in {MajorPOS.VERB, MajorPOS.ADJECTIVE}:
            group_end = find_group_end(tokens,curr_idx)
            group_length = group_end - curr_idx
            new_verb_token = join_tokens(original_text,tokens, curr_idx, group_length)
            output_token_list.append(new_verb_token)
            curr_idx += group_length
        else:
            output_token_list.append(
                TokenGroup(
                    text=curr_token.text,
                    lookup_form=curr_token.dictionary_form,
                    start_idx=curr_token.start_idx,
                    end_idx=curr_token.end_idx,
                    tokens=[curr_token]
                )
            )
            curr_idx += 1
    return output_token_list
