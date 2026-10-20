from fastapi import FastAPI
from app.parser import parse_japanese_text
from app.grouping import regroup_tokens
from app.schemas import ParseJapaneseRequest

app = FastAPI()

@app.post("/jap/parse")
def get_tokenized_text(request : ParseJapaneseRequest):
    text = request.text
    tokens =  parse_japanese_text(text)
    return regroup_tokens(text, tokens)