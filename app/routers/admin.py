from typing import Dict, Optional
from fastapi import APIRouter, Depends, Body
from app.security import get_api_key
from app.services.nlp import reload_models

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_api_key)])

@router.post("/reload-models")
def admin_reload_models(
    payload: Dict = Body(
        default={},
        example={
            "emotion_model": "SamLowe/roberta-base-go_emotions",
            "toxicity_model": "unitary/unbiased-toxic-roberta",
            "sarcasm_model": "cardiffnlp/twitter-roberta-base-sarcasm"
        },
    ),
) -> Dict:
    result = reload_models(
        emotion_model=payload.get("emotion_model"),
        toxicity_model=payload.get("toxicity_model"),
        sarcasm_model=payload.get("sarcasm_model"),
    )
    return {"ok": True, **result}
