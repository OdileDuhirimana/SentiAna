from typing import Dict, List
from fastapi import APIRouter, Depends, Body
from app.security import get_api_key
from app.services.nlp import engine

router = APIRouter(prefix="/domain", tags=["domain"], dependencies=[Depends(get_api_key)])

@router.post("/support")
def support_urgency(
    payload: Dict = Body(..., example={"text": "I have been waiting for hours. This is unacceptable.", "lang_hint": "en"}),
) -> Dict:
    text: str = payload.get("text", "").strip()
    lang_hint = payload.get("lang_hint")
    if not text:
        return {"error": "text is required"}
    res = engine.analyze(text=text, lang_hint=lang_hint)
    emo = {e["label"]: float(e["score"]) for e in res.get("emotions", [])}
    tox = res.get("toxicity", {})

    # Heuristic urgency score: combines anger/annoyance/fear + toxicity + sarcasm
    anger = emo.get("anger", 0.0)
    annoyance = emo.get("annoyance", 0.0)
    fear = emo.get("fear", 0.0)
    urgency = 0.5*max(anger, annoyance) + 0.3*fear + 0.2*max(tox.values()) if tox else 0.5*max(anger,annoyance)+0.3*fear
    urgency = float(min(1.0, max(0.0, urgency)))

    tier = "low"
    if urgency >= 0.75:
        tier = "critical"
    elif urgency >= 0.5:
        tier = "high"
    elif urgency >= 0.25:
        tier = "medium"

    return {"language": res.get("language"), "urgency": urgency, "tier": tier, "emotions": res.get("emotions"), "toxicity": tox}

@router.post("/reviews")
def product_review_analysis(
    payload: Dict = Body(..., example={"text": "The food is great but the service is horrible.", "lang_hint": "en"}),
) -> Dict:
    text: str = payload.get("text", "").strip()
    lang_hint = payload.get("lang_hint")
    if not text:
        return {"error": "text is required"}
    res = engine.analyze(text=text, lang_hint=lang_hint)
    # Use extracted keywords as aspects; assign coarse sentiment using polarity proxy from emotions
    aspects = res.get("aspects", [])
    emo = {e["label"]: float(e["score"]) for e in res.get("emotions", [])}
    pos = sum(emo.get(k, 0.0) for k in ["joy","admiration","excitement","amusement","gratitude","pride","relief","love"]) 
    neg = sum(emo.get(k, 0.0) for k in ["sadness","anger","disappointment","annoyance","disgust","embarrassment","fear","grief","remorse"]) 
    polarity = pos - neg
    sentiment = "positive" if polarity > 0.1 else ("negative" if polarity < -0.1 else "mixed")
    for a in aspects:
        a["sentiment"] = sentiment
    return {"language": res.get("language"), "aspects": aspects, "polarity": polarity, "emotions": res.get("emotions")}

@router.post("/mental-health")
def mental_health_signal(
    payload: Dict = Body(..., example={"text": "I feel hopeless and overwhelmed.", "lang_hint": "en"}),
) -> Dict:
    text: str = payload.get("text", "").strip()
    lang_hint = payload.get("lang_hint")
    if not text:
        return {"error": "text is required"}
    res = engine.analyze(text=text, lang_hint=lang_hint)
    emo = {e["label"]: float(e["score"]) for e in res.get("emotions", [])}
    risk = float(min(1.0, emo.get("sadness",0.0)*0.4 + emo.get("grief",0.0)*0.3 + emo.get("fear",0.0)*0.2 + emo.get("remorse",0.0)*0.1))
    level = "low"
    if risk >= 0.75:
        level = "high"
    elif risk >= 0.5:
        level = "medium"
    return {"language": res.get("language"), "risk": risk, "level": level, "emotions": res.get("emotions")}

@router.post("/social")
def social_media_guard(
    payload: Dict = Body(..., example={"text": "Great job ignoring my complaint again 🙃", "lang_hint": "en"}),
) -> Dict:
    text: str = payload.get("text", "").strip()
    lang_hint = payload.get("lang_hint")
    if not text:
        return {"error": "text is required"}
    res = engine.analyze(text=text, lang_hint=lang_hint)
    toxic = res.get("toxicity", {})
    sarcasm = res.get("sarcasm", {})
    sarc_score = float(max(sarcasm.values()) if sarcasm else 0.0)
    top_toxic = sorted(((k, float(v)) for k, v in toxic.items()), key=lambda x: x[1], reverse=True)[:3]
    return {
        "language": res.get("language"),
        "top_toxic_signals": top_toxic,
        "sarcasm_likelihood": sarc_score,
        "emotions": res.get("emotions"),
    }
