"""Account preferences shared across clients."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import current_user_id
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/profile", tags=["profile"])


class Profile(BaseModel):
    learning_language: Literal["ja", "en"]


@router.get("", response_model=Profile)
def read_profile(db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return Profile(learning_language=user.learning_language)


@router.put("", response_model=Profile)
def update_profile(profile: Profile, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.learning_language = profile.learning_language
    db.commit()
    return profile
