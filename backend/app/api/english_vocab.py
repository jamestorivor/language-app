from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import DEVELOPMENT_USER_ID
from app.db.models.english_vocab import EnglishDictionary, EnglishWordFamiliarity
from app.db.session import get_db
from app.schemas import GroupToken, ParseJapaneseRequest, UpdateFamiliarityScoreRequest, UpdateFamiliarityScoreResponse
from app.services.english_vocab import parse_english_text

router = APIRouter()


@router.post("/eng/parse", response_model=list[GroupToken])
def parse_english(request: ParseJapaneseRequest, db: Session = Depends(get_db)):
    return parse_english_text(db, request.text, DEVELOPMENT_USER_ID)


@router.patch("/eng/update_familiarity_score", response_model=UpdateFamiliarityScoreResponse)
def update_english_familiarity(request: UpdateFamiliarityScoreRequest, db: Session = Depends(get_db)):
    if db.get(EnglishDictionary, request.word_id) is None:
        raise HTTPException(status_code=404, detail="English word not found")
    key = (DEVELOPMENT_USER_ID, request.word_id)
    progress = db.get(EnglishWordFamiliarity, key)
    if progress is None:
        progress = EnglishWordFamiliarity(user_id=key[0], word_id=key[1], familiarity_score=request.new_score)
        db.add(progress)
    else:
        progress.familiarity_score = request.new_score
    db.commit()
    return UpdateFamiliarityScoreResponse(word_id=request.word_id, new_score=request.new_score)
