from app.schemas import JapaneseTokenizedResponse, MajorPOS, PartOfSpeech, TokenGroup


# Every pattern starts with a 動詞 token.
# Every ending token must have major POS 助動詞.
#
# Pattern:
# (rule_name, verb_conjugation_form_prefix, ending_tokens)
#
# Ending token:
# (surface, dictionary_form)
VERB_ENDING_PATTERNS = (
    (
        "polite_negative_past",
        "連用形",
        (
            ("ませ", "ます"),
            ("ん", "ぬ"),
            ("でし", "です"),
            ("た", "た"),
        ),
    ),
    (
        "polite_negative",
        "連用形",
        (
            ("ませ", "ます"),
            ("ん", "ぬ"),
        ),
    ),
    (
        "polite_past",
        "連用形",
        (
            ("まし", "ます"),
            ("た", "た"),
        ),
    ),
    (
        "negative_past",
        "未然形",
        (
            ("なかっ", "ない"),
            ("た", "た"),
        ),
    ),
    (
        "polite",
        "連用形",
        (
            ("ます", "ます"),
        ),
    ),
    (
        "negative",
        "未然形",
        (
            ("ない", "ない"),
        ),
    ),
    (
        "desire",
        "連用形",
        (
            ("たい", "たい"),
        ),
    ),
)

def get_verb_group_length(tokens : list[JapaneseTokenizedResponse], start_index : int):
    # begin forming group
    # Go through all verb patterns
    head = tokens[start_index]

    best_group_len = 1 # Verb only

    for (_, verb_conjugation_form_prefix, ending_tokens) in VERB_ENDING_PATTERNS:
        head_pos = PartOfSpeech.from_sudachi(head.part_of_speech)
        if not head_pos.conjugation_form.startswith(verb_conjugation_form_prefix):
            continue

        previous_token = head
        match = True
        for offset, (surface, dictionary_form) in enumerate(ending_tokens):
            curr_token_idx = offset + 1 + start_index
            curr_token = tokens[curr_token_idx]

            if (
                curr_token.start_idx != previous_token.end_idx 
                or curr_token.part_of_speech[0] != "助動詞"
                or curr_token.text != surface 
                or curr_token.dictionary_form != dictionary_form
            ):
                match = False
                break
            else :
                previous_token = curr_token
        if match:
            curr_group_len = len(ending_tokens) + 1
            best_group_len = max(curr_group_len, best_group_len)

    return best_group_len

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
        if major_part_of_speech == MajorPOS.VERB:
            verb_group_length = get_verb_group_length(tokens,curr_idx)
            new_verb_token = join_tokens(original_text,tokens, curr_idx, verb_group_length)
            output_token_list.append(new_verb_token)
            curr_idx += verb_group_length
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
