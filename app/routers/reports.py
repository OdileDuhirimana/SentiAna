from typing import Dict, List
from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse, JSONResponse
from io import StringIO
import csv
from app.security import get_api_key
from app.services.store import store

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(get_api_key)])

@router.get("/timeline/{conv_id}.json")
def report_timeline_json(conv_id: str = Path(...)) -> JSONResponse:
    data = store.get_timeline(conv_id)
    return JSONResponse(content=data)

@router.get("/timeline/{conv_id}.csv")
def report_timeline_csv(conv_id: str = Path(...)) -> StreamingResponse:
    data = store.get_timeline(conv_id)
    buf = StringIO()
    writer = csv.writer(buf)
    # header
    writer.writerow(["ts", "language", "top_emotion", "top_emotion_score", "toxicity_max", "sarcasm_max"])
    for item in data:
        ts = item.get("ts")
        language = item.get("language")
        emotions = item.get("emotions") or []
        top_label = emotions[0]["label"] if emotions else None
        top_score = emotions[0]["score"] if emotions else None
        toxicity = item.get("toxicity") or {}
        tox_max = max((float(v) for v in toxicity.values()), default=0.0)
        sarcasm = item.get("sarcasm") or {}
        sarc_max = max((float(v) for v in sarcasm.values()), default=0.0)
        writer.writerow([ts, language, top_label, top_score, tox_max, sarc_max])
    buf.seek(0)
    return StreamingResponse(buf, media_type='text/csv')

@router.get("/summary/{conv_id}.csv")
def report_summary_csv(conv_id: str = Path(...)) -> StreamingResponse:
    # Produce a simple summary with counts of top emotions
    data = store.get_timeline(conv_id)
    from collections import Counter
    counter = Counter()
    for item in data:
        emotions = item.get("emotions") or []
        if emotions:
            counter[emotions[0]["label"]] += 1
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["emotion", "count"])
    for k, v in counter.most_common():
        writer.writerow([k, v])
    buf.seek(0)
    return StreamingResponse(buf, media_type='text/csv')
