from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import japanese_vocab, podcast

app = FastAPI()

app.include_router(japanese_vocab.router)
app.include_router(podcast.router)
app.include_router(japanese_vocab.router, prefix="/api")
app.include_router(podcast.router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Use your actual frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)
