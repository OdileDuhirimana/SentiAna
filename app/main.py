from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.routers.analyze import router as analyze_router
from app.routers.timeline import router as timeline_router
from app.routers.xai import router as xai_router
from app.routers.zeroshot import router as zeroshot_router
from app.routers.moderation import router as moderation_router
from app.routers.domain import router as domain_router
from app.routers.meta import router as meta_router
from app.routers.agent import router as agent_router
from app.routers.admin import router as admin_router
from app.routers.reports import router as reports_router
from app.routers.integrations import router as integrations_router
from app.routers.feedback import router as feedback_router
from app.routers.analytics import router as analytics_router
from app.rate_limit import SlidingWindowRateLimiter
from app.security import API_KEY
from app.db import init_db

app = FastAPI(title="SentimentScope API", version="0.1.0")


def parse_origins(raw: str) -> list[str]:
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["*"]


allowed_origins = parse_origins(os.getenv("CORS_ALLOWED_ORIGINS", "*"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic sliding-window rate limiting (60 req/min per IP per route)
app.add_middleware(SlidingWindowRateLimiter, requests=60, window_seconds=60)

@app.on_event("startup")
def _startup():
    try:
        init_db()
    except Exception:
        # Do not block startup on DB init errors; endpoints may still work sans DB
        pass

app.include_router(analyze_router, prefix="/api")
app.include_router(timeline_router, prefix="/api")
app.include_router(xai_router, prefix="/api")
app.include_router(zeroshot_router, prefix="/api")
app.include_router(moderation_router, prefix="/api")
app.include_router(domain_router, prefix="/api")
app.include_router(meta_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")

# Serve minimal dashboard
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
app.mount("/clients", StaticFiles(directory="clients"), name="clients")

@app.get("/")
def root():
    return {"status": "ok", "name": "SentimentScope", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"ok": True}

@app.websocket("/ws/analyze")
async def ws_analyze(websocket: WebSocket):
    # Enforce API key if configured
    api_key_header = websocket.headers.get("x-api-key") or websocket.headers.get("X-API-Key")
    # Support browser clients by allowing api_key in query params
    api_key_query = websocket.query_params.get("api_key")
    provided = api_key_header or api_key_query
    if API_KEY is not None and provided != API_KEY:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    try:
        from app.services.nlp import engine
        # Optional language hint from query string
        lang_hint = websocket.query_params.get("lang_hint")
        while True:
            data = await websocket.receive_text()
            result = engine.analyze(text=data, lang_hint=lang_hint)
            await websocket.send_json(result)
    except WebSocketDisconnect:
        pass
