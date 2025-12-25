from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.core.textproc import normalize_text, tokenize_text, remove_stopwords

router = APIRouter()

class TextIn(BaseModel):
    raw_text: str

@router.post("/preprocess")
def preprocess_text_endpoint(item: TextIn):
    normalized = normalize_text(item.raw_text)
    tokens = tokenize_text(normalized)
    filtered = remove_stopwords(tokens)

    return {
        "original": item.raw_text,
        "normalized": normalized,
        "tokens": tokens,
        "filtered_tokens": filtered,
        "total_tokens": len(tokens),
        "total_filtered": len(filtered),
    }