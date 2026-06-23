from typing import Dict
from fastapi import APIRouter, Depends, Body
from app.security import get_api_key
from app.services.nlp import engine

router = APIRouter(prefix="/agent", tags=["agent"], dependencies=[Depends(get_api_key)])

# Template-based empathetic reply suggestion based on detected emotions

TEMPLATES = {
    "sadness": "I'm really sorry you're going through this. I hear you, and I want to help. Could you share a bit more about what would make this better for you?",
    "anger": "Thank you for telling us. I understand how frustrating this is. I'm here to help fix it right away—let me start by ...",
    "fear": "I can see this is concerning. You're not alone—we're here with you. Let's walk through this together step by step.",
    "disappointment": "I appreciate your honesty. This fell short of expectations, and that's on us. Here's what I'll do next ...",
    "joy": "That's wonderful to hear! Thank you for sharing this. Is there anything else we can do to keep this going?",
    "admiration": "We really appreciate your kind words. We'll pass this along to the team!",
    "annoyance": "Thanks for flagging this. I get how inconvenient this is. I'll take care of it and keep you updated.",
}

DEFAULT_REPLY = "Thanks for sharing this. I understand how you feel, and I'm here to help. Could you tell me a bit more so I can resolve it quickly?"

@router.post("/reply")
def suggest_reply(payload: Dict = Body(..., example={"text": "I waited an hour and no one helped me.", "lang_hint": "en"})) -> Dict:
    text = (payload.get("text") or '').strip()
    lang_hint = payload.get("lang_hint")
    if not text:
        return {"error": "text is required"}
    res = engine.analyze(text=text, lang_hint=lang_hint)
    emotions = res.get("emotions", [])
    top = emotions[0]["label"] if emotions else None
    # Choose best template among top few emotions
    choice = None
    for e in emotions[:3]:
        if e["label"] in TEMPLATES:
            choice = TEMPLATES[e["label"]]
            break
    reply = choice or DEFAULT_REPLY
    return {"language": res.get("language"), "reply": reply, "top_emotion": top, "emotions": emotions}
