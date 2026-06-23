import os
import json
import asyncio
import websockets
import requests
from typing import Dict, List, Optional, Any, AsyncIterator

class SentimentScopeClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv('SENTIMENTSCOPE_API_KEY')
        self.headers = {'Content-Type': 'application/json'}
        if self.api_key:
            self.headers['X-API-Key'] = self.api_key

    # ---- REST ----
    def analyze(self, text: str, lang_hint: Optional[str] = None) -> Dict[str, Any]:
        payload = {'text': text, 'lang_hint': lang_hint}
        r = requests.post(f"{self.base_url}/api/analyze/", headers=self.headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()

    def explain(self, text: str) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/api/xai/explain", headers=self.headers, json={'text': text}, timeout=60)
        r.raise_for_status()
        return r.json()

    def zeroshot(self, text: str, labels: List[str], multi_label: bool = True) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/api/zeroshot/", headers=self.headers, json={'text': text, 'labels': labels, 'multi_label': multi_label}, timeout=60)
        r.raise_for_status()
        return r.json()

    def moderate(self, text: str, threshold: float = 0.6) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/api/moderate/", headers=self.headers, json={'text': text, 'threshold': threshold}, timeout=60)
        r.raise_for_status()
        return r.json()

    def support_urgency(self, text: str) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/api/domain/support", headers=self.headers, json={'text': text}, timeout=60)
        r.raise_for_status()
        return r.json()

    def review_analysis(self, text: str) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/api/domain/reviews", headers=self.headers, json={'text': text}, timeout=60)
        r.raise_for_status()
        return r.json()

    def mental_health(self, text: str) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/api/domain/mental-health", headers=self.headers, json={'text': text}, timeout=60)
        r.raise_for_status()
        return r.json()

    def agent_reply(self, text: str) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/api/agent/reply", headers=self.headers, json={'text': text}, timeout=60)
        r.raise_for_status()
        return r.json()

    # ---- Feedback + Analytics + Admin ----
    def submit_feedback(self, text: str, lang_hint: Optional[str] = None, company_id: Optional[str] = None, source: Optional[str] = None) -> Dict[str, Any]:
        payload = {'text': text, 'lang_hint': lang_hint, 'company_id': company_id, 'source': source}
        r = requests.post(f"{self.base_url}/api/feedback/", headers=self.headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()

    def analytics_overview(self, company_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        params = {}
        if company_id:
            params['company_id'] = company_id
        if days:
            params['days'] = str(days)
        r = requests.get(f"{self.base_url}/api/analytics/overview", headers=self.headers, params=params, timeout=60)
        r.raise_for_status()
        return r.json()

    def admin_reload_models(self, emotion_model: Optional[str] = None, toxicity_model: Optional[str] = None, sarcasm_model: Optional[str] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {'emotion_model': emotion_model, 'toxicity_model': toxicity_model, 'sarcasm_model': sarcasm_model}
        r = requests.post(f"{self.base_url}/api/admin/reload-models", headers=self.headers, json=body, timeout=60)
        r.raise_for_status()
        return r.json()

    # ---- Timeline ----
    def timeline_append(self, conv_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/api/timeline/{conv_id}", headers=self.headers, json=item, timeout=30)
        r.raise_for_status()
        return r.json()

    def timeline_get(self, conv_id: str) -> List[Dict[str, Any]]:
        r = requests.get(f"{self.base_url}/api/timeline/{conv_id}", headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json()

    def timeline_summary(self, conv_id: str) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/api/timeline/{conv_id}/summary", headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json()

    # ---- WebSocket ----
    async def ws_analyze(self, text_stream: AsyncIterator[str]) -> AsyncIterator[Dict[str, Any]]:
        headers = {}
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        uri = f"{self.base_url.replace('http','ws')}/ws/analyze"
        async with websockets.connect(uri, extra_headers=headers, ping_interval=None) as ws:
            async for msg in text_stream:
                await ws.send(msg)
                data = await ws.recv()
                yield json.loads(data)
