import logging
import time

from app.auth import current_user_id
from app.observability import log_event
from fastapi import APIRouter, Depends
from app.services.japanese_vocab.parser import parse_japanese_text
from app.services.japanese_vocab.grouping import regroup_tokens, add_db_data_to_tokens
from app.schemas import ParseJapaneseRequest, GroupToken, UpdateFamiliarityScoreRequest, UpdateFamiliarityScoreResponse
from app.data_access.japanese_vocab import update_db_familiarity_score
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.japanese_vocab.dictionary_expressions import find_dictionary_expressions

router = APIRouter()

@router.post("/jap/parse")
def get_tokenized_text(request : ParseJapaneseRequest, db : Session = Depends(get_db), user_id: int = Depends(current_user_id)) -> list[GroupToken]:
    start = time.perf_counter()
    text = request.text
    tokens = parse_japanese_text(text)
    tokenized_at = time.perf_counter()
    dictionary_matches = find_dictionary_expressions(db, tokens)
    matched_at = time.perf_counter()
    grouped_tokens = regroup_tokens(text, tokens, dictionary_matches)
    enriched_tokens = add_db_data_to_tokens(db, grouped_tokens, user_id)
    finished = time.perf_counter()
    log_event(logging.INFO, "japanese_parse_completed", characters=len(text),
              token_count=len(tokens), group_count=len(grouped_tokens),
              tokenize_ms=round((tokenized_at - start) * 1000, 1),
              match_ms=round((matched_at - tokenized_at) * 1000, 1),
              enrich_ms=round((finished - matched_at) * 1000, 1))
    return enriched_tokens

@router.patch("/jap/update_familiarity_score")
def update_familiarity_score(request : UpdateFamiliarityScoreRequest, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)) -> UpdateFamiliarityScoreResponse :
    new_score = request.new_score
    word_id = request.word_id
    update_response : UpdateFamiliarityScoreResponse = update_db_familiarity_score(db, user_id, word_id, new_score )
    return update_response
