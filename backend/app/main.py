from fastapi import FastAPI

app = FastAPI()

DEVELOPMENT_USER_ID = 1

from app.api import japanese_vocab, podcast

app.include_router(podcast.router)
