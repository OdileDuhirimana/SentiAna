from typing import Dict
from fastapi import APIRouter

router = APIRouter(prefix="/meta", tags=["meta"])

@router.get("/models")
def models() -> Dict:
    return {
        "emotion_model": "SamLowe/roberta-base-go_emotions",
        "toxicity_model": "unitary/unbiased-toxic-roberta",
        "sarcasm_model": "cardiffnlp/twitter-roberta-base-sarcasm",
        "translation": {
            "fr->en": "Helsinki-NLP/opus-mt-fr-en",
            "sw->en": "Helsinki-NLP/opus-mt-sw-en",
        },
        "zeroshot_model": "facebook/bart-large-mnli",
        "version": "0.1.0",
    }
