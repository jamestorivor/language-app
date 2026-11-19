from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.config import DEVELOPMENT_USER_ID
from app.db.models.english_vocab import EnglishDictionary, EnglishWordFamiliarity
from app.db.models.japanese_vocab import JapaneseDictionary, JapaneseWordFamiliarity
from app.db.session import get_db
from app.db.models.study import WordStudyFamiliarity
from app.db.models.english_study import EnglishStudyFamiliarity
from app.services.study_membership import refresh_manual_familiarity

router = APIRouter()
LEVELS = {"ja": ("N5", "N4", "N3", "N2", "N1"),
          "en": ("A1", "A2", "B1", "B2", "C1", "C2")}


class MarkKnownRequest(BaseModel):
    language: Literal["ja", "en"]
    level: str


class MarkKnownResponse(BaseModel):
    matched_words: int


@router.post("/vocabulary/mark-known", response_model=MarkKnownResponse)
def mark_known(request: MarkKnownRequest, db: Session = Depends(get_db)):
    levels = LEVELS[request.language]
    if request.level not in levels:
        raise HTTPException(status_code=422, detail="Invalid level for language")
    included = levels[:levels.index(request.level) + 1]
    if request.language == "ja":
        dictionary, progress, level_column = JapaneseDictionary, JapaneseWordFamiliarity, JapaneseDictionary.jlpt_level
    else:
        dictionary, progress, level_column = EnglishDictionary, EnglishWordFamiliarity, EnglishDictionary.cefr_level
    study_familiarity = WordStudyFamiliarity if request.language == "ja" else EnglishStudyFamiliarity
    memberships = db.scalars(select(study_familiarity).join(
        dictionary, study_familiarity.word_id == dictionary.word_id
    ).where(study_familiarity.user_id == DEVELOPMENT_USER_ID, level_column.in_(included))
        .order_by(study_familiarity.word_id).with_for_update()).all()
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else postgres_insert
    statement = insert(progress).from_select(
        ["user_id", "word_id", "familiarity_score"],
        select(DEVELOPMENT_USER_ID, dictionary.word_id, 5).where(level_column.in_(included)),
    )
    statement = statement.on_conflict_do_update(
        index_elements=[progress.user_id, progress.word_id],
        set_={"familiarity_score": 5},
    ).returning(progress.word_id)
    matched_words = len(db.scalars(statement).all())
    for membership in memberships:
        refresh_manual_familiarity(db, membership, 5)
    db.commit()
    return MarkKnownResponse(matched_words=matched_words)
