export class SentimentScopeClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey || (typeof process !== 'undefined' ? process.env.SENTIMENTSCOPE_API_KEY : undefined);
    this.headers = { 'Content-Type': 'application/json' };
    if (this.apiKey) this.headers['X-API-Key'] = this.apiKey;
  }

  async analyze(text, langHint = null) {
    const res = await fetch(`${this.baseUrl}/api/analyze/`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ text, lang_hint: langHint })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async explain(text) {
    const res = await fetch(`${this.baseUrl}/api/xai/explain`, {
      method: 'POST', headers: this.headers, body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async zeroshot(text, labels, multiLabel = true) {
    const res = await fetch(`${this.baseUrl}/api/zeroshot/`, {
      method: 'POST', headers: this.headers, body: JSON.stringify({ text, labels, multi_label: multiLabel })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async moderate(text, threshold = 0.6) {
    const res = await fetch(`${this.baseUrl}/api/moderate/`, {
      method: 'POST', headers: this.headers, body: JSON.stringify({ text, threshold })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async supportUrgency(text) {
    const res = await fetch(`${this.baseUrl}/api/domain/support`, {
      method: 'POST', headers: this.headers, body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async reviewAnalysis(text) {
    const res = await fetch(`${this.baseUrl}/api/domain/reviews`, {
      method: 'POST', headers: this.headers, body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async mentalHealth(text) {
    const res = await fetch(`${this.baseUrl}/api/domain/mental-health`, {
      method: 'POST', headers: this.headers, body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async agentReply(text) {
    const res = await fetch(`${this.baseUrl}/api/agent/reply`, {
      method: 'POST', headers: this.headers, body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async timelineAppend(convId, item) {
    const res = await fetch(`${this.baseUrl}/api/timeline/${encodeURIComponent(convId)}`, {
      method: 'POST', headers: this.headers, body: JSON.stringify(item)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async timelineGet(convId) {
    const res = await fetch(`${this.baseUrl}/api/timeline/${encodeURIComponent(convId)}`, { headers: this.headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async timelineSummary(convId) {
    const res = await fetch(`${this.baseUrl}/api/timeline/${encodeURIComponent(convId)}/summary`, { headers: this.headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  // Feedback storage (DB-backed)
  async submitFeedback({ text, langHint = null, companyId = null, source = null }) {
    const payload = { text, lang_hint: langHint, company_id: companyId, source };
    const res = await fetch(`${this.baseUrl}/api/feedback/`, {
      method: 'POST', headers: this.headers, body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  // Analytics
  async analyticsOverview({ companyId = null, days = 30 } = {}) {
    const qs = new URLSearchParams();
    if (companyId) qs.set('company_id', companyId);
    if (days) qs.set('days', String(days));
    const res = await fetch(`${this.baseUrl}/api/analytics/overview?${qs.toString()}`, { headers: this.headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  // Admin
  async adminReloadModels({ emotionModel = null, toxicityModel = null, sarcasmModel = null } = {}) {
    const body = { emotion_model: emotionModel, toxicity_model: toxicityModel, sarcasm_model: sarcasmModel };
    const res = await fetch(`${this.baseUrl}/api/admin/reload-models`, { method: 'POST', headers: this.headers, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  // WebSocket stream
  connectWebSocket(opts = {}) {
    const url = this.baseUrl.replace('http', 'ws') + '/ws/analyze';
    const qs = new URLSearchParams();
    if (this.apiKey) qs.set('api_key', this.apiKey);
    const langHint = opts.langHint ?? null;
    if (langHint) qs.set('lang_hint', langHint);
    const wsUrl = qs.toString() ? `${url}?${qs.toString()}` : url;
    return new WebSocket(wsUrl);
  }
}
