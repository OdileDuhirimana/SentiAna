from typing import Dict, Any
from fastapi import APIRouter, Depends, Body
from app.security import get_api_key
from app.services.nlp import engine

router = APIRouter(prefix="/integrations", tags=["integrations"], dependencies=[Depends(get_api_key)])

@router.post("/zendesk/webhook")
def zendesk_webhook(event: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    # Expecting a minimal body containing a ticket comment
    text = (
        event.get("comment")
        or event.get("ticket", {}).get("comment")
        or event.get("message")
        or ""
    )
    text = str(text).strip()
    if not text:
        return {"ok": True, "skipped": True}
    res = engine.analyze(text=text)
    toxic = res.get("toxicity", {})
    decision = "allow"
    if max((float(v) for v in toxic.values()), default=0.0) >= 0.8:
        decision = "block"
    elif max((float(v) for v in toxic.values()), default=0.0) >= 0.5:
        decision = "review"
    return {"ok": True, "analysis": res, "decision": decision}

@router.post("/intercom/webhook")
def intercom_webhook(event: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    text = (
        event.get("data", {}).get("item", {}).get("conversation_message", {}).get("body")
        or event.get("message")
        or ""
    )
    text = str(text)
    # Strip rudimentary HTML tags if present
    text = text.replace("<br>", "\n").replace("<p>", " ").replace("</p>", " ")
    text = text.strip()
    if not text:
        return {"ok": True, "skipped": True}
    res = engine.analyze(text=text)
    toxic = res.get("toxicity", {})
    decision = "allow"
    if max((float(v) for v in toxic.values()), default=0.0) >= 0.8:
        decision = "block"
    elif max((float(v) for v in toxic.values()), default=0.0) >= 0.5:
        decision = "review"
    return {"ok": True, "analysis": res, "decision": decision}
