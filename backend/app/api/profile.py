"""Account preferences shared across clients."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user_id
from app.api.vocabulary_levels import LEVELS, MarkKnownRequest, mark_known_words
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/profile", tags=["profile"])


class Profile(BaseModel):
    learning_language: Literal["ja", "en"]


class ProfileWithOnboarding(Profile):
    onboarding_required: bool
    levels: dict[str, str | None]


class ProfileLevel(BaseModel):
    language: Literal["ja", "en"]
    level: str | None


class OnboardingResult(Profile):
    matched_words: int | None


class Onboarding(Profile):
    level: str | None = None


@router.get("", response_model=ProfileWithOnboarding)
def read_profile(db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return ProfileWithOnboarding(learning_language=user.learning_language, onboarding_required=not user.learning_language_selected,
                                 levels={"ja": user.japanese_level, "en": user.english_level})


@router.put("", response_model=Profile)
def update_profile(profile: Profile, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.learning_language = profile.learning_language
    user.learning_language_selected = True
    db.commit()
    return profile


@router.put("/level", response_model=ProfileLevel)
def update_level(choice: ProfileLevel, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    if choice.level is not None and choice.level not in LEVELS[choice.language]:
        raise HTTPException(status_code=422, detail="Invalid level for language")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    setattr(user, "japanese_level" if choice.language == "ja" else "english_level", choice.level)
    db.commit()
    return choice


@router.post("/onboarding", response_model=OnboardingResult)
def complete_onboarding(choice: Onboarding, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.learning_language_selected:
        raise HTTPException(status_code=409, detail="Onboarding already completed")
    matched_words = None
    if choice.level is not None:
        matched_words = mark_known_words(MarkKnownRequest(language=choice.learning_language, level=choice.level), db, user_id).matched_words
    setattr(user, "japanese_level" if choice.learning_language == "ja" else "english_level", choice.level)
    user.learning_language = choice.learning_language
    user.learning_language_selected = True
    db.commit()
    return OnboardingResult(learning_language=choice.learning_language, matched_words=matched_words)
