from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import english_vocab, japanese_vocab, podcast
from app.observability import RequestLoggingMiddleware

app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)

app.include_router(japanese_vocab.router)
app.include_router(english_vocab.router)
app.include_router(podcast.router)
app.include_router(japanese_vocab.router, prefix="/api")
app.include_router(english_vocab.router, prefix="/api")
app.include_router(podcast.router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Use your actual frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
