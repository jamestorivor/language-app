"""Authenticate Clerk sessions and resolve them to local data owners."""
import os

from clerk_backend_api import AuthenticateRequestOptions, authenticate_request
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.session import get_db


def current_user_id(request: Request, db: Session = Depends(get_db)) -> int:
    secret = os.getenv("CLERK_SECRET_KEY")
    jwt_key = os.getenv("CLERK_JWT_KEY", "").replace("\\n", "\n")
    parties = [part.strip() for part in os.getenv("CLERK_AUTHORIZED_PARTIES", "").split(",") if part.strip()]
    if not (secret or jwt_key) or not parties:
        raise HTTPException(status_code=503, detail="Authentication is not configured")

    # Accept only explicit bearer tokens. Never rely on cross-origin cookies.
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer ") or not authorization[7:].strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required", headers={"WWW-Authenticate": "Bearer"})
    state = authenticate_request(request, AuthenticateRequestOptions(
        secret_key=secret, jwt_key=jwt_key or None, authorized_parties=parties,
        accepts_token=["session_token"],
    ))
    payload = state.payload if state.is_signed_in else None
    if not payload or not isinstance(payload.get("sub"), str) or not payload["sub"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session", headers={"WWW-Authenticate": "Bearer"})

    clerk_id = payload["sub"]
    user = db.scalar(select(User).where(User.clerk_id == clerk_id))
    if user is None:
        user = User(clerk_id=clerk_id, name=clerk_id)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            # Two first requests for the same account can arrive concurrently.
            db.rollback()
            user = db.scalar(select(User).where(User.clerk_id == clerk_id))
            if user is None:
                raise
        else:
            db.refresh(user)
    return user.id
