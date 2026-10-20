from fastapi import FastAPI
from .parser import parse_japanese_text

app = FastAPI()

@app.get("/jap/parse")
def get_tokenized_text(text):
    return parse_japanese_text(text)