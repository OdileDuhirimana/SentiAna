from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    lang_hint: Optional[str] = None

class EmotionScore(BaseModel):
    label: str
    score: float

class AspectItem(BaseModel):
    aspect: str
    sentiment: Optional[str] = None

class AnalyzeResponse(BaseModel):
    language: str
    emotions: List[EmotionScore]
    toxicity: Dict[str, float]
    sarcasm: Dict[str, float]
    aspects: List[AspectItem]
