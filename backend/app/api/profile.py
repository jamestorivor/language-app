"""Account preferences shared across clients."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user_id
from app.api.vocabulary_levels import MarkKnownRequest, mark_known_words
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/profile", tags=["profile"])


class Profile(BaseModel):
    learning_language: Literal["ja", "en"]


class ProfileWithOnboarding(Profile):
    onboarding_required: bool


class Onboarding(Profile):
    level: str | None = None


@router.get("", response_model=ProfileWithOnboarding)
def read_profile(db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return ProfileWithOnboarding(learning_language=user.learning_language, onboarding_required=not user.learning_language_selected)


@router.put("", response_model=Profile)
def update_profile(profile: Profile, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.learning_language = profile.learning_language
    user.learning_language_selected = True
    db.commit()
    return profile


@router.post("/onboarding", response_model=Profile)
def complete_onboarding(choice: Onboarding, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.learning_language_selected:
        raise HTTPException(status_code=409, detail="Onboarding already completed")
    if choice.level is not None:
        mark_known_words(MarkKnownRequest(language=choice.learning_language, level=choice.level), db, user_id)
    user.learning_language = choice.learning_language
    user.learning_language_selected = True
    db.commit()
    return Profile(learning_language=choice.learning_language)
