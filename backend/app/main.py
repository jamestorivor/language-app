from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import english_vocab, japanese_vocab, podcast, profile, study, vocabulary_levels
from app.observability import RequestLoggingMiddleware

app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)

app.include_router(japanese_vocab.router)
app.include_router(english_vocab.router)
app.include_router(podcast.router)
app.include_router(vocabulary_levels.router)
app.include_router(study.router)
app.include_router(profile.router)
app.include_router(japanese_vocab.router, prefix="/api")
app.include_router(english_vocab.router, prefix="/api")
app.include_router(podcast.router, prefix="/api")
app.include_router(vocabulary_levels.router, prefix="/api")
app.include_router(study.router, prefix="/api")
app.include_router(profile.router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://language-app-jamestorivors-projects.vercel.app",
        "https://language-app-two-gamma.vercel.app",
        "https://honne.space",
        "https://www.honne.space",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
