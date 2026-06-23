from typing import Dict, List
from fastapi import APIRouter, Depends, Path, Body
from app.security import get_api_key
from app.services.store import store

router = APIRouter(prefix="/timeline", tags=["timeline"], dependencies=[Depends(get_api_key)])

@router.post("/{conv_id}")
def append_timeline(
    conv_id: str = Path(..., min_length=1),
    item: Dict = Body(..., description="Arbitrary payload; typically includes language, emotions, toxicity, etc."),
) -> Dict:
    store.append_timeline(conv_id, item)
    return {"ok": True}

@router.get("/{conv_id}")
def get_timeline(conv_id: str = Path(..., min_length=1)) -> List[Dict]:
    return store.get_timeline(conv_id)

# ---- Simple summary/forecast ----

# Basic valence mapping for a subset of GoEmotions labels
POSITIVE = {"joy", "admiration", "excitement", "amusement", "gratitude", "pride", "relief", "love"}
NEGATIVE = {"sadness", "anger", "disappointment", "annoyance", "disgust", "embarrassment", "fear", "grief", "remorse"}

@router.get("/{conv_id}/summary")
def get_summary(conv_id: str = Path(..., min_length=1)) -> Dict:
    import numpy as np  # local import to avoid overhead if unused

    data = store.get_timeline(conv_id)
    if not data:
        return {"count": 0, "dominant_emotion": None, "trend": None}

    # Aggregate label scores across timeline
    label_scores: Dict[str, float] = {}
    pos_series = []
    neg_series = []

    for point in data:
        emotions = point.get("emotions") or []
        one = {e.get("label"): float(e.get("score", 0.0)) for e in emotions}
        for k, v in one.items():
            label_scores[k] = label_scores.get(k, 0.0) + v
        pos_series.append(sum(one.get(lbl, 0.0) for lbl in POSITIVE))
        neg_series.append(sum(one.get(lbl, 0.0) for lbl in NEGATIVE))

    dominant_emotion = max(label_scores.items(), key=lambda kv: kv[1])[0]

    # Simple linear trend on (pos - neg)
    y = np.array(pos_series) - np.array(neg_series)
    x = np.arange(len(y))
    slope = float(np.polyfit(x, y, 1)[0]) if len(y) >= 2 else 0.0

    trend = "rising" if slope > 0.01 else ("falling" if slope < -0.01 else "stable")

    return {
        "count": len(data),
        "dominant_emotion": dominant_emotion,
        "trend": trend,
        "slope": slope,
    }
