from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.security import get_api_key
from app.schemas import AnalyzeResponse
from app.services.nlp import engine
from app.db import get_db
from app.models import Feedback

router = APIRouter(prefix="/feedback", tags=["feedback"], dependencies=[Depends(get_api_key)])


class FeedbackIn(BaseModel):
    text: str
    lang_hint: Optional[str] = None
    company_id: Optional[str] = None
    source: Optional[str] = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("'text' must not be empty")
        return v.strip()


@router.post("/", response_model=AnalyzeResponse)
async def submit_feedback(payload: FeedbackIn, db: Session = Depends(get_db)) -> AnalyzeResponse:
    text = payload.text
    lang_hint = payload.lang_hint
    company_id = payload.company_id
    source = payload.source

    # Analyze
    res = engine.analyze(text=text, lang_hint=lang_hint)

    # Persist
    fb = Feedback(
        company_id=company_id,
        source=source,
        text_original=text,
        text_en=res.get("text_en", text),
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
