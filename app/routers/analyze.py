from fastapi import APIRouter, Depends
from app.schemas import AnalyzeRequest, AnalyzeResponse, EmotionScore, AspectItem
from app.services.nlp import engine
from app.security import get_api_key

router = APIRouter(prefix="/analyze", tags=["analyze"], dependencies=[Depends(get_api_key)])

@router.post("/", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    res = engine.analyze(text=req.text, lang_hint=req.lang_hint)
    return AnalyzeResponse(
        language=res["language"],
        emotions=[EmotionScore(**e) for e in res["emotions"]],
        toxicity=res["toxicity"],
        sarcasm=res["sarcasm"],
        aspects=[AspectItem(**a) for a in res["aspects"]],
    )
