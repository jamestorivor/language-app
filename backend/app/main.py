from fastapi import FastAPI
from app.parser import parse_japanese_text
from app.grouping import regroup_tokens

app = FastAPI()

@app.get("/jap/parse")
def get_tokenized_text(text):
    tokens =  parse_japanese_text(text)
    return regroup_tokens(text, tokens)