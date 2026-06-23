from typing import Dict
from fastapi import APIRouter, Depends, Body
from app.security import get_api_key
from app.services.nlp import engine

router = APIRouter(prefix="/moderate", tags=["moderation"], dependencies=[Depends(get_api_key)])

@router.post("/")
def moderate(
    payload: Dict = Body(..., example={"text": "You are an idiot. I will find you." , "threshold": 0.6, "lang_hint": "en"}),
) -> Dict:
    text: str = payload.get("text", "").strip()
    threshold: float = float(payload.get("threshold", 0.6))
    lang_hint = payload.get("lang_hint")
    if not text:
        return {"error": "text is required"}

    res = engine.analyze(text=text, lang_hint=lang_hint)
    tox = res.get("toxicity", {})
    flags = {k: float(v) for k, v in tox.items() if float(v) >= threshold}

    decision = "allow"
    if any(lbl in flags for lbl in ["threat", "identity_attack", "hate", "severe_toxicity"]):
        decision = "block"
    elif flags:
        decision = "review"

    return {
        "language": res.get("language"),
        "toxicity": tox,
        "flags": flags,
        "decision": decision,
        "threshold": threshold,
    }
