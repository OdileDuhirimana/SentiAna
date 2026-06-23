from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.security import get_api_key
from app.schemas import AnalyzeResponse
from app.services.nlp import engine
from app.db import get_db
from app.models import Feedback

router = APIRouter(prefix="/feedback", tags=["feedback"], dependencies=[Depends(get_api_key)])


class FeedbackIn:
    # Minimal inline model to avoid expanding schemas.py for now
    # fields: text, lang_hint?, company_id?, source?
    def __init__(self, text: str, lang_hint: Optional[str] = None, company_id: Optional[str] = None, source: Optional[str] = None):
        self.text = text
        self.lang_hint = lang_hint
        self.company_id = company_id
        self.source = source


@router.post("/", response_model=AnalyzeResponse)
async def submit_feedback(payload: dict, db: Session = Depends(get_db)) -> AnalyzeResponse:
    # Extract with defaults
    text = str(payload.get("text", "")).strip()
    if not text:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="'text' is required")
    lang_hint = payload.get("lang_hint")
    company_id = payload.get("company_id")
    source = payload.get("source")

    # Analyze
    res = engine.analyze(text=text, lang_hint=lang_hint)

    # Persist
    fb = Feedback(
        company_id=company_id,
        source=source,
        text_original=text,
        text_en=payload.get("text_en") or (text if res.get("language") == "en" else payload.get("text_en") or text),
        language=res.get("language", "en"),
        emotions_json=res.get("emotions"),
        toxicity_json=res.get("toxicity"),
        sarcasm_json=res.get("sarcasm") or {},
        aspects_json=res.get("aspects") or [],
    )
    db.add(fb)
    db.commit()

    return AnalyzeResponse(
        language=res["language"],
        emotions=res["emotions"],
        toxicity=res["toxicity"],
        sarcasm=res.get("sarcasm", {}),
        aspects=res.get("aspects", []),
    )
