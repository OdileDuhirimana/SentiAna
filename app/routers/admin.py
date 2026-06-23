from typing import Dict, Optional
from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from app.security import get_api_key
from app.services.nlp import reload_models

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_api_key)])


class ReloadModelsPayload(BaseModel):
    emotion_model: Optional[str] = None
    toxicity_model: Optional[str] = None
    sarcasm_model: Optional[str] = None


@router.post("/reload-models")
def admin_reload_models(payload: Optional[ReloadModelsPayload] = Body(default=None)) -> Dict:
    if payload is None:
        payload = ReloadModelsPayload()
    result = reload_models(
        emotion_model=payload.emotion_model,
        toxicity_model=payload.toxicity_model,
        sarcasm_model=payload.sarcasm_model,
    )
    return {"ok": True, **result}
