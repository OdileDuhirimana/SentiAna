from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.security import get_api_key
from app.db import get_db
from app.models import Feedback

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_api_key)])

POSITIVE = {"joy", "admiration", "excitement", "amusement", "gratitude", "pride", "relief", "love", "optimism"}
NEGATIVE = {"sadness", "anger", "disappointment", "annoyance", "disgust", "embarrassment", "fear", "grief", "remorse"}


def satisfaction_from_emotions(emotions: List[Dict]) -> float:
    if not emotions:
        return 0.0
    one = {e.get("label"): float(e.get("score", 0.0)) for e in emotions}
    pos = sum(one.get(lbl, 0.0) for lbl in POSITIVE)
    neg = sum(one.get(lbl, 0.0) for lbl in NEGATIVE)
    return pos - neg


@router.get("/overview")
async def analytics_overview(
    db: Session = Depends(get_db),
    company_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
):
    since = datetime.utcnow() - timedelta(days=days)
    stmt = select(Feedback).where(Feedback.created_at >= since)
    if company_id:
        stmt = stmt.where(Feedback.company_id == company_id)
    stmt = stmt.order_by(Feedback.created_at.asc())

    rows = list(db.execute(stmt).scalars())

    # Build series
    series = []
    dist: Dict[str, float] = {}
    suggestions: Dict[str, int] = {}

    for r in rows:
        s = satisfaction_from_emotions(r.emotions_json or [])
        series.append({
            "t": r.created_at.isoformat() if r.created_at else None,
            "satisfaction": s,
        })
        for e in (r.emotions_json or []):
            lbl = e.get("label")
            dist[lbl] = dist.get(lbl, 0.0) + float(e.get("score", 0.0))
        # simple suggestions from aspects
        for a in (r.aspects_json or []):
            asp = a.get("aspect")
            if asp:
                suggestions[asp] = suggestions.get(asp, 0) + 1

    # Trend (simple linear regression on satisfaction)
    slope = 0.0
    trend = "stable"
    if len(series) >= 2:
        import numpy as np
        y = np.array([p["satisfaction"] for p in series], dtype=float)
        x = np.arange(len(y))
        slope_val = float(np.polyfit(x, y, 1)[0])
        slope = slope_val
        trend = "rising" if slope_val > 0.01 else ("falling" if slope_val < -0.01 else "stable")

    top_suggestions = sorted(suggestions.items(), key=lambda kv: kv[1], reverse=True)[:15]
    dist_sorted = sorted(dist.items(), key=lambda kv: kv[1], reverse=True)[:12]

    return {
        "count": len(rows),
        "series": series,
        "emotion_distribution": [{"label": k, "value": v} for k, v in dist_sorted],
        "trend": trend,
        "slope": slope,
        "suggestions": [{"text": k, "count": v} for k, v in top_suggestions],
    }
