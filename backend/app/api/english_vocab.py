from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import current_user_id
from app.db.models.english_vocab import EnglishDictionary, EnglishWordFamiliarity
from app.db.session import get_db
from app.schemas import GroupToken, ParseJapaneseRequest, UpdateFamiliarityScoreRequest, UpdateFamiliarityScoreResponse
from app.services.english_vocab import parse_english_text
from app.services.study_membership import lock_word_study, refresh_manual_familiarity

router = APIRouter()


@router.post("/eng/parse", response_model=list[GroupToken])
def parse_english(request: ParseJapaneseRequest, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    return parse_english_text(db, request.text, user_id)


@router.patch("/eng/update_familiarity_score", response_model=UpdateFamiliarityScoreResponse)
def update_english_familiarity(request: UpdateFamiliarityScoreRequest, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    if db.get(EnglishDictionary, request.word_id) is None:
        raise HTTPException(status_code=404, detail="English word not found")
    membership = lock_word_study(db, user_id, request.word_id, "en")
    key = (user_id, request.word_id)
    progress = db.get(EnglishWordFamiliarity, key)
    if progress is None:
        progress = EnglishWordFamiliarity(user_id=key[0], word_id=key[1], familiarity_score=request.new_score)
        db.add(progress)
    else:
        progress.familiarity_score = request.new_score
    refresh_manual_familiarity(db, membership, request.new_score)
    db.commit()
    return UpdateFamiliarityScoreResponse(word_id=request.word_id, new_score=request.new_score)
