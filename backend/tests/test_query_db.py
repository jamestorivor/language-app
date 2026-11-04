from app.data_access.japanese_vocab import get_word_details
from app.services.japanese_vocab.parser import parse_japanese_text
from app.services.japanese_vocab.grouping import regroup_tokens
from app.schemas import JapaneseTokenizedResponse, GroupToken

TEST_USER_ID = 1

# text = "猫が食べます。"
# tokens : list[JapaneseTokenizedResponse] = parse_japanese_text(text)

# group_tokens : list[GroupToken] = regroup_tokens(text,tokens)

# for token in group_tokens:
#     print(get_word_details(token, TEST_USER_ID))