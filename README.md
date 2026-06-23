# SentimentScope — Emotion Intelligence API

Production-ready FastAPI microservice for multi-label emotion analysis, toxicity and sarcasm detection, simple aspect extraction, multilingual support (FR/SW via translation), WebSocket streaming, and basic security + rate limiting.

## Quickstart

- Python 3.10+
- First run downloads model weights (few minutes)

Install and run:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Docker:

```bash
docker build -t sentimentscope .
docker run -e SENTIMENTSCOPE_API_KEY="your-secret-key" -p 8000:8000 sentimentscope
```

## REST API

Endpoint: `POST /api/analyze/`

Headers:
- `Content-Type: application/json`
- `X-API-Key: your-secret-key` (required if env var is set)

Request body:
```json
{
  "text": "Great job ignoring my complaint again 🙃",
  "lang_hint": null
}
```

Response shape:
```json
{
  "language": "en",
  "emotions": [{"label":"annoyance","score":0.82}, ...],
  "toxicity": {"toxic":0.12, ...},
  "sarcasm": {"sarcasm":0.76, ...},
  "aspects": [{"aspect":"complaint","sentiment":null}, ...]
}
```

Examples:

```bash
# English
curl -X POST 'http://localhost:8000/api/analyze/' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-secret-key' \
  -d '{"text":"Great job ignoring my complaint again 🙃"}'

# French (auto-translated FR->EN)
curl -X POST 'http://localhost:8000/api/analyze/' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-secret-key' \
  -d '{"text":"Le service est horrible mais la nourriture est bonne"}'
```

## WebSocket Streaming

URL: `ws://localhost:8000/ws/analyze`

Headers:
- `X-API-Key: your-secret-key` (required if env var is set)

Flow:
- Connect
- Send a text message
- Receive JSON analysis per message

Example (wscat):
```bash
npx wscat -c ws://localhost:8000/ws/analyze -H 'X-API-Key: your-secret-key'
> Food is good but service is horrible
< {"language":"en","emotions":[...],"toxicity":{...},"sarcasm":{...},"aspects":[...]}
```

## Timeline API

Optional conversation tracking and simple trend summary. If `REDIS_URL` is set, timelines are stored in Redis; otherwise in-memory.

Append an item:

```bash
curl -X POST 'http://localhost:8000/api/timeline/conv123' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-secret-key' \
  -d '{"emotions":[{"label":"anger","score":0.7}], "toxicity":{"toxic":0.2}}'
```

Fetch:

```bash
curl -H 'X-API-Key: your-secret-key' 'http://localhost:8000/api/timeline/conv123'
```

Summary/forecast:

```bash
curl -H 'X-API-Key: your-secret-key' 'http://localhost:8000/api/timeline/conv123/summary'
```

## Features in this MVP
- Multi-label emotions (GoEmotions)
- Toxicity detection (unbiased-toxic-roberta)
- Sarcasm detection (twitter-roberta-sarcasm)
- Keyword-based aspect hints (YAKE)
- FR & SW translation to EN (MarianMT)
- In-memory caching
- Sliding-window rate limiting (60 req/min/IP/route)
- API key security (optional via env)
- Dockerized

## Notes
- Kinyarwanda (`rw`) is detected but not translated; analysis runs on raw text.
- First inference per model is slower due to cold start and weights download.
- This is an MVP; advanced modules (XAI heatmaps, domain-specific heads, analytics dashboard) can be added next.

## Environment variables
- `SENTIMENTSCOPE_API_KEY` – optional API key required for REST and WebSocket when set
- `REDIS_URL` – optional Redis connection URL for timeline storage (e.g., `redis://localhost:6379/0`)

## Additional Endpoints
- **Zero-shot**: `POST /api/zeroshot/` → `{ text, labels[], multi_label? }`
- **Explainable AI**: `POST /api/xai/explain` → token weights via LIME
- **Moderation**: `POST /api/moderate/` → allow/review/block + flags
- **Domain**:
  - Support urgency: `POST /api/domain/support`
  - Product reviews: `POST /api/domain/reviews`
  - Mental health signal: `POST /api/domain/mental-health`
  - Social media guard: `POST /api/domain/social`
- **Agent**: `POST /api/agent/reply` → empathetic reply suggestion
- **Timeline reports**:
  - JSON: `GET /api/reports/timeline/{conv_id}.json`
  - CSV timeline: `GET /api/reports/timeline/{conv_id}.csv`
  - CSV summary: `GET /api/reports/summary/{conv_id}.csv`
- **Meta/Models**: `GET /api/meta/models`
- **Admin**: `POST /api/admin/reload-models` → set `EMOTION_MODEL`, `TOXICITY_MODEL`, `SARCASM_MODEL`
- **Integrations (stubs)**:
  - Zendesk webhook: `POST /api/integrations/zendesk/webhook`
  - Intercom webhook: `POST /api/integrations/intercom/webhook`

## Auth
- API Key: send header `X-API-Key: <key>` if `SENTIMENTSCOPE_API_KEY` is set.
- WebSocket: include header if possible or use `ws://.../ws/analyze?api_key=<key>`.
- Optional JWT: set `JWT_SECRET`; use `Authorization: Bearer <token>`.

## SDK Usage

Python
```python
from clients.python.sentimentscope import SentimentScopeClient
c = SentimentScopeClient('http://localhost:8000', api_key='your-secret-key')
res = c.analyze('Food is good but service is horrible')
zs = c.zeroshot('I feel numb', ['joy','sadness','anger','fear'])
mod = c.moderate('You are an idiot. I will find you.', threshold=0.6)
```

JavaScript
```js
import { SentimentScopeClient } from './clients/js/sentimentscope.js';
const c = new SentimentScopeClient('http://localhost:8000', 'your-secret-key');
const res = await c.analyze('Great job ignoring my complaint again 🙃');
```

## Dashboard
- Minimal dashboard served at `http://localhost:8000/dashboard` (analyze form + live WS preview).
