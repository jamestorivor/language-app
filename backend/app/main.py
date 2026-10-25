from fastapi import FastAPI, Depends
from app.parser import parse_japanese_text
from app.grouping import regroup_tokens, add_db_data_to_tokens
from app.schemas import ParseJapaneseRequest, GroupToken, UpdateFamiliarityScoreRequest, UpdateFamiliarityScoreResponse
from app.db.query_jap_db import update_db_familiarity_score
from sqlalchemy.orm import Session
from app.db.session import get_db

app = FastAPI()

DEVELOPMENT_USER_ID = 1

@app.post("/jap/parse")
def get_tokenized_text(request : ParseJapaneseRequest, db : Session = Depends(get_db)) -> list[GroupToken]:
    text = request.text
    tokens =  parse_japanese_text(text)
    grouped_tokens = regroup_tokens(text, tokens)
    enriched_tokens = add_db_data_to_tokens(db, grouped_tokens, DEVELOPMENT_USER_ID)
    return enriched_tokens

@app.patch("/jap/update_familiarity_score")
def update_familiarity_score(request : UpdateFamiliarityScoreRequest, db: Session = Depends(get_db)) -> UpdateFamiliarityScoreResponse :
    new_score = request.new_score
    word_id = request.word_id
    update_response : UpdateFamiliarityScoreResponse = update_db_familiarity_score(db, DEVELOPMENT_USER_ID, word_id, new_score )
    return update_response
