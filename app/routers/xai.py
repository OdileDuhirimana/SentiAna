from typing import Dict, List
from fastapi import APIRouter, Depends, Body
from app.security import get_api_key
from app.services.nlp import engine

# Lightweight word-importance using LIME TextExplainer
router = APIRouter(prefix="/xai", tags=["xai"], dependencies=[Depends(get_api_key)])

@router.post("/explain")
def explain(
    payload: Dict = Body(..., example={"text": "Food is good but service is horrible", "lang_hint": "en"}),
) -> Dict:
    text: str = payload.get("text", "").strip()
    lang_hint = payload.get("lang_hint")
    if not text:
        return {"error": "text is required"}

    try:
        from lime.lime_text import LimeTextExplainer  # type: ignore
    except Exception:
        # Fallback: return top emotions without attributions
        res = engine.analyze(text=text, lang_hint=lang_hint)
        return {"language": res["language"], "emotions": res["emotions"], "tokens": []}

    res = engine.analyze(text=text, lang_hint=lang_hint)
    # Build a prediction function for LIME to score emotions (one-vs-rest on top label)
    top_label = res["emotions"][0]["label"] if res.get("emotions") else None

    def predict_proba(texts: List[str]):
        import numpy as np
        out = []
        for t in texts:
            r = engine.analyze(text=t, lang_hint=lang_hint)
            mapping = {e["label"]: e["score"] for e in r.get("emotions", [])}
            # binary: [1 - p(top), p(top)]
            p = float(mapping.get(top_label, 0.0)) if top_label else 0.0
            out.append([1.0 - p, p])
        return np.array(out)

    explainer = LimeTextExplainer(class_names=["other", top_label or "target"]) 
    exp = explainer.explain_instance(text, predict_proba, num_features=10)
    tokens = [{"token": w, "weight": float(s)} for w, s in exp.as_list()]

    return {
        "language": res.get("language"),
        "target_emotion": top_label,
        "emotions": res.get("emotions"),
        "toxicity": res.get("toxicity"),
        "sarcasm": res.get("sarcasm"),
        "tokens": tokens,
    }
