from typing import Dict, List
from fastapi import APIRouter, Depends, Body
from app.security import get_api_key
from transformers import pipeline
from app.services.nlp import engine

router = APIRouter(prefix="/zeroshot", tags=["zero-shot"], dependencies=[Depends(get_api_key)])

_zeroshot = None

def get_zeroshot():
    global _zeroshot
    if _zeroshot is None:
        _zeroshot = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    return _zeroshot

@router.post("/")
def classify(
    payload: Dict = Body(..., example={"text": "I feel numb and exhausted", "labels": ["joy","sadness","anger","fear","excitement"], "lang_hint": "en"}),
) -> Dict:
    text: str = payload.get("text", "").strip()
    labels: List[str] = payload.get("labels") or []
    multi_label: bool = bool(payload.get("multi_label", True))
    lang_hint = payload.get("lang_hint")
    if not text or not labels:
        return {"error": "text and labels are required"}
    # Translate non-English text to English for BART NLI
    if lang_hint and lang_hint in {"fr", "sw", "rw"}:
        try:
            text = engine._translate_to_en(text, lang_hint)  # type: ignore[attr-defined]
        except Exception:
            pass
    clf = get_zeroshot()
    res = clf(text, candidate_labels=labels, multi_label=multi_label)
    return {"sequence": res.get("sequence"), "labels": res.get("labels"), "scores": [float(s) for s in res.get("scores", [])]}
