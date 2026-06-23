import { SentimentScopeClient } from '/clients/js/sentimentscope.js';

const e = React.createElement;

function App() {
  const defaultBase = localStorage.getItem('ss_base') || window.location.origin;
  const [baseUrl, setBaseUrl] = React.useState(defaultBase);
  const [apiKey, setApiKey] = React.useState(localStorage.getItem('ss_key') || '');
  const [text, setText] = React.useState('Food is good but service is horrible');
  const [langHint, setLangHint] = React.useState(''); // '' = auto, else: en, fr, sw, rw
  const [result, setResult] = React.useState(null);
  const [wsConnected, setWsConnected] = React.useState(false);
  const [wsMessages, setWsMessages] = React.useState([]);
  const [convId, setConvId] = React.useState('demo');
  const [loading, setLoading] = React.useState({ analyze:false, explain:false, zs:false, mod:false, domain:false, fb:false, analytics:false });
  const [toasts, setToasts] = React.useState([]);
  const [companyId, setCompanyId] = React.useState('acme');
  const [source, setSource] = React.useState('webform');
  const [analytics, setAnalytics] = React.useState(null);
  const [analyticsDays, setAnalyticsDays] = React.useState(30);

  const client = React.useMemo(() => new SentimentScopeClient(baseUrl, apiKey), [baseUrl, apiKey]);

  React.useEffect(() => { localStorage.setItem('ss_base', baseUrl); }, [baseUrl]);
  React.useEffect(() => { localStorage.setItem('ss_key', apiKey); }, [apiKey]);

  // Auto-correct a common mismatch: user opened dashboard on :8081 but base points to :8000
  React.useEffect(() => {
    const origin = window.location.origin;
    if (baseUrl && baseUrl.includes('localhost:8000') && origin !== baseUrl) {
      setBaseUrl(origin);
    }
  }, []);

  function EmotionDistributionBars({ dist }) {
    if (!dist || !dist.length) return e('p', { className: 'text-sm text-gray-500' }, 'No data');
    const max = dist[0].value || 1;
    return e('div', { className: 'space-y-2' }, dist.map((it, idx) => (
      e('div', { key: it.label+idx }, [
        e('div', { className: 'flex justify-between text-sm mb-1' }, [
          e('span', null, it.label), e('span', null, (it.value*100).toFixed(1)+'%')
        ]),
        e('div', { className: 'w-full bg-gray-200 rounded h-2' }, [
          e('div', { className: 'bg-indigo-600 h-2 rounded', style: { width: `${Math.min(100, (it.value/max)*100)}%` } })
        ])
      ])
    )));
  }

  function SatisfactionTrend({ series }) {
    if (!series || series.length < 2) return e('p', { className: 'text-sm text-gray-500' }, 'Not enough data');
    const vals = series.map(p => Number(p.satisfaction||0));
    const min = Math.min(...vals), max = Math.max(...vals);
    const norm = vals.map(v => max===min ? 50 : ((v-min)/(max-min))*100);
    return e('div', { className: 'flex gap-1 items-end h-16' }, norm.map((v,i)=>
      e('div', { key: i, className: 'bg-emerald-700 w-2 rounded', style: { height: `${Math.max(4, v)}%` } })
    ));
  }

  // ---- Timeline tools ----
  const [timeline, setTimeline] = React.useState([]);
  const [summary, setSummary] = React.useState(null);

  async function onSaveToTimeline() {
    if (!result) { pushToast('Run Analyze first to get a result to save.'); return; }
    try {
      setLoading(s => ({...s, timelineSave:true}));
      const payload = {
        ts: Date.now()/1000,
        language: result.language,
        emotions: result.emotions,
        toxicity: result.toxicity,
        sarcasm: result.sarcasm || {},
        text
      };
      const res = await fetch(`${baseUrl}/api/timeline/${encodeURIComponent(convId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey || '' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(await res.text());
      pushToast('Saved to timeline');
    } catch (e) {
      pushToast('Timeline save error: ' + e.message);
    } finally { setLoading(s => ({...s, timelineSave:false})); }
  }

  async function onGetTimeline() {
    try {
      setLoading(s => ({...s, timelineGet:true}));
      const res = await fetch(`${baseUrl}/api/timeline/${encodeURIComponent(convId)}`, {
        headers: { 'X-API-Key': apiKey || '' }
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setTimeline(data);
      pushToast(`Loaded ${data.length} timeline items`);
    } catch (e) {
      pushToast('Timeline load error: ' + e.message);
    } finally { setLoading(s => ({...s, timelineGet:false})); }
  }

  async function onGetSummary() {
    try {
      setLoading(s => ({...s, timelineSummary:true}));
      const res = await fetch(`${baseUrl}/api/timeline/${encodeURIComponent(convId)}/summary`, {
        headers: { 'X-API-Key': apiKey || '' }
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSummary(data);
    } catch (e) {
      pushToast('Summary load error: ' + e.message);
    } finally { setLoading(s => ({...s, timelineSummary:false})); }
  }

  async function onAnalyze(evn) {
    evn.preventDefault();
    try {
      setLoading(s => ({...s, analyze:true}));
      // Use REST directly to include lang_hint support
      const res = await fetchJson('/api/analyze/', { text, lang_hint: langHint || null });
      setResult(res);
    } catch (err) {
      pushToast('Analyze error: ' + err);
    }
    finally { setLoading(s => ({...s, analyze:false})); }
  }

  // Generic helper for calling other endpoints using Base URL + API key
  async function fetchJson(path, body) {
    const res = await fetch(`${baseUrl}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey || ''
      },
      body: JSON.stringify(body || {})
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${t}`);
    }
    return res.json();
  }

  async function onSubmitFeedback() {
    try {
      setLoading(s => ({...s, fb:true}));
      const res = await fetch(`${baseUrl}/api/feedback/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey || '' },
        body: JSON.stringify({ text, lang_hint: langHint || null, company_id: companyId || null, source: source || null })
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResult(data);
      pushToast('Feedback submitted');
    } catch (e) {
      pushToast('Submit error: ' + e.message);
    } finally { setLoading(s => ({...s, fb:false})); }
  }

  async function onLoadAnalytics() {
    try {
      setLoading(s => ({...s, analytics:true}));
      const params = new URLSearchParams();
      if (companyId) params.set('company_id', companyId);
      if (analyticsDays) params.set('days', String(analyticsDays));
      const res = await fetch(`${baseUrl}/api/analytics/overview?` + params.toString(), {
        headers: { 'X-API-Key': apiKey || '' }
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setAnalytics(data);
      pushToast(`Loaded analytics (${data.count})`);
    } catch (e) {
      pushToast('Analytics error: ' + e.message);
    } finally { setLoading(s => ({...s, analytics:false})); }
  }

  function pushToast(msg) {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, msg }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }

  // XAI Explain
  const [explain, setExplain] = React.useState(null);
  async function onExplain() {
    try {
      setLoading(s => ({...s, explain:true}));
      const data = await fetchJson('/api/xai/explain', { text, lang_hint: langHint || null });
      setExplain(data);
    } catch (e) {
      pushToast('Explain error: ' + e.message);
    }
    finally { setLoading(s => ({...s, explain:false})); }
  }

  // Zero-shot classification
  const [zsLabels, setZsLabels] = React.useState('joy,sadness,anger,fear');
  const [zsMulti, setZsMulti] = React.useState(true);
  const [zsResult, setZsResult] = React.useState(null);
  async function onZeroShot() {
    const labels = zsLabels.split(',').map(s => s.trim()).filter(Boolean);
    try {
      setLoading(s => ({...s, zs:true}));
      const data = await fetchJson('/api/zeroshot/', { text, labels, multi_label: !!zsMulti, lang_hint: langHint || null });
      setZsResult(data);
    } catch (e) {
      pushToast('Zero-shot error: ' + e.message);
    }
    finally { setLoading(s => ({...s, zs:false})); }
  }

  // Moderation
  const [modThreshold, setModThreshold] = React.useState(0.6);
  const [modResult, setModResult] = React.useState(null);
  async function onModerate() {
    try {
      setLoading(s => ({...s, mod:true}));
      const data = await fetchJson('/api/moderate/', { text, threshold: Number(modThreshold), lang_hint: langHint || null });
      setModResult(data);
    } catch (e) {
      pushToast('Moderation error: ' + e.message);
    }
    finally { setLoading(s => ({...s, mod:false})); }
  }

  // Domain endpoints
  const [domain, setDomain] = React.useState('support');
  const [domainResult, setDomainResult] = React.useState(null);
  async function onDomain() {
    try {
      setLoading(s => ({...s, domain:true}));
      const data = await fetchJson(`/api/domain/${domain}`, { text, lang_hint: langHint || null });
      setDomainResult(data);
    } catch (e) {
      pushToast('Domain error: ' + e.message);
    }
    finally { setLoading(s => ({...s, domain:false})); }
  }

  function connectWS() {
    const ws = client.connectWebSocket({ langHint: langHint || null });
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        setWsMessages(prev => [data, ...prev].slice(0, 50));
      } catch {}
    };
    // send entered text once connected
    const interval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(text);
        clearInterval(interval);
      }
    }, 200);
  }

  function EmotionList({ emotions }) {
    if (!emotions) return null;
    return e('ul', { className: 'list-disc pl-5' }, emotions.slice(0, 8).map((it, idx) => e('li', { key: idx }, `${it.label}: ${(it.score*100).toFixed(1)}%`)));
  }

  function EmotionBars({ emotions }) {
    if (!emotions) return null;
    const sorted = [...emotions].sort((a,b) => b.score - a.score).slice(0, 8);
    function colorFor(label){
      const L = label.toLowerCase();
      if (['anger','annoyance','disgust'].includes(L)) return 'bg-rose-600';
      if (['sadness','grief'].includes(L)) return 'bg-blue-600';
      if (['joy','amusement','excitement','gratitude','love','admiration','pride'].includes(L)) return 'bg-emerald-600';
      if (['fear','nervousness'].includes(L)) return 'bg-amber-600';
      if (['neutral','realization','curiosity','surprise','confusion','relief','desire','approval','disapproval','optimism','caring','embarrassment','remorse'].includes(L)) return 'bg-gray-600';
      return 'bg-indigo-600';
    }
    return e('div', { className: 'space-y-2' }, sorted.map((it, idx) => (
      e('div', { key: `${it.label}-${idx}` }, [
        e('div', { className: 'flex justify-between text-sm mb-1' }, [
          e('span', { key: 'lbl' }, it.label),
          e('span', { key: 'pct' }, `${(it.score*100).toFixed(1)}%`),
        ]),
        e('div', { className: 'w-full bg-gray-200 rounded h-2' }, [
          e('div', { className: `${colorFor(it.label)} h-2 rounded`, style: { width: `${Math.min(100, it.score*100)}%` } })
        ])
      ])
    )));
  }

  function ToxicityList({ toxicity }) {
    if (!toxicity) return null;
    const entries = Object.entries(toxicity).sort((a,b) => b[1]-a[1]).slice(0, 8);
    return e('ul', { className: 'list-disc pl-5 text-sm' }, entries.map(([k,v]) => e('li', { key: k }, `${k}: ${(v*100).toFixed(2)}%`)));
  }

  function PolarityBar({ polarity }) {
    if (!polarity) return null;
    const neg = Number(polarity.negative||0), neu = Number(polarity.neutral||0), pos = Number(polarity.positive||0);
    const total = Math.max(1e-6, neg+neu+pos);
    const pn = Math.round((neg/total)*100), pu = Math.round((neu/total)*100), pp = 100 - pn - pu;
    return e('div', { className: 'w-full bg-gray-200 rounded h-3 flex overflow-hidden' }, [
      e('div', { key:'neg', className: 'bg-rose-600 h-3', style: { width: `${pn}%` } }),
      e('div', { key:'neu', className: 'bg-gray-500 h-3', style: { width: `${pu}%` } }),
      e('div', { key:'pos', className: 'bg-emerald-600 h-3', style: { width: `${pp}%` } })
    ]);
  }

  function SarcasmList({ sarcasm }) {
    if (!sarcasm || !Object.keys(sarcasm).length) return null;
    const entries = Object.entries(sarcasm).sort((a,b)=> b[1]-a[1]).slice(0,5);
    return e('ul', { className: 'list-disc pl-5 text-sm' }, entries.map(([k,v]) => e('li', { key:k }, `${k}: ${(v*100).toFixed(1)}%`)));
  }

  function AspectList({ aspects }) {
    if (!aspects || !aspects.length) return null;
    return e('ul', { className: 'list-disc pl-5 text-sm' }, aspects.map((a, i) => e('li', { key: i }, `${a.aspect}: ${a.sentiment || 'n/a'}`)));
  }

  // Simple charts for timeline
  const POSITIVE = new Set(['joy','admiration','excitement','amusement','gratitude','pride','relief','love','optimism']);
  const NEGATIVE = new Set(['sadness','anger','disappointment','annoyance','disgust','embarrassment','fear','grief','remorse']);

  function TimelineDistribution({ items }) {
    if (!items || !items.length) return e('p', { className: 'text-sm text-gray-500' }, 'No timeline data');
    const totals = {};
    items.forEach(pt => {
      (pt.emotions||[]).forEach(e => {
        totals[e.label] = (totals[e.label]||0) + Number(e.score||0);
      });
    });
    const sorted = Object.entries(totals).sort((a,b)=>b[1]-a[1]).slice(0,10);
    const max = sorted.length ? sorted[0][1] : 1;
    return e('div', { className: 'space-y-2' }, sorted.map(([label, val]) => (
      e('div', { key: label }, [
        e('div', { className: 'flex justify-between text-sm mb-1' }, [
          e('span', null, label), e('span', null, (val*100).toFixed(1)+'%')
        ]),
        e('div', { className: 'w-full bg-gray-200 rounded h-2' }, [
          e('div', { className: 'bg-indigo-600 h-2 rounded', style: { width: `${Math.min(100, (val/max)*100)}%` } })
        ])
      ])
    )));
  }

  function TimelineTrend({ items }) {
    if (!items || items.length < 2) return e('p', { className: 'text-sm text-gray-500' }, 'Not enough data');
    const series = items.map(pt => {
      const one = Object.fromEntries((pt.emotions||[]).map(e=>[e.label, Number(e.score||0)]));
      const pos = Array.from(POSITIVE).reduce((s,l)=> s + (one[l]||0), 0);
      const neg = Array.from(NEGATIVE).reduce((s,l)=> s + (one[l]||0), 0);
      return pos - neg;
    });
    const min = Math.min(...series), max = Math.max(...series);
    const norm = series.map(v => max===min ? 50 : ((v-min)/(max-min))*100);
    // Sparkline style bars
    return e('div', { className: 'flex gap-1 items-end h-16' }, norm.map((v,i)=>
      e('div', { key: i, className: 'bg-gray-700 w-2 rounded', style: { height: `${Math.max(4, v)}%` } })
    ));
  }

  function topEmotion(emotions){
    if (!emotions || !emotions.length) return null;
    return emotions.reduce((a,b)=> (a.score>b.score?a:b));
  }

  function maxToxicity(tox){
    if (!tox) return 0;
    return Object.values(tox).reduce((m,v)=> Math.max(m, v || 0), 0);
  }

  return e('div', { className: 'space-y-6 relative' }, [
    // Toasts
    e('div', { className: 'fixed right-4 top-4 space-y-2 z-50' }, toasts.map(t => e('div', { key: t.id, className: 'bg-black/80 text-white px-3 py-2 rounded shadow' }, t.msg))),
    e('h1', { key: 'title', className: 'text-2xl font-bold' }, 'SentimentScope Dashboard'),

    // Quick stats when result exists
    result ? e('div', { className: 'grid grid-cols-1 md:grid-cols-3 gap-4' }, [
      e('div', { key: 'stat1', className: 'p-3 bg-white rounded shadow flex items-center justify-between' }, [
        e('div', { className: 'text-sm text-gray-600' }, 'Top Emotion'),
        (() => { const te = topEmotion(result.emotions); return e('span', { className: 'px-2 py-1 rounded text-white text-sm ' + (te ? 'bg-indigo-600' : 'bg-gray-400') }, te ? `${te.label} ${(te.score*100).toFixed(1)}%` : 'n/a'); })()
      ]),
      e('div', { key: 'stat2', className: 'p-3 bg-white rounded shadow flex items-center justify-between' }, [
        e('div', { className: 'text-sm text-gray-600' }, 'Max Toxicity'),
        e('span', { className: 'px-2 py-1 rounded bg-rose-600 text-white text-sm' }, `${(maxToxicity(result.toxicity)*100).toFixed(2)}%`)
      ]),
      e('div', { key: 'stat3', className: 'p-3 bg-white rounded shadow flex items-center justify-between' }, [
        e('div', { className: 'text-sm text-gray-600' }, 'Language'),
        e('span', { className: 'px-2 py-1 rounded bg-gray-700 text-white text-sm' }, result.language || 'n/a')
      ])
    ]) : null,

    e('div', { className: 'grid grid-cols-1 md:grid-cols-2 gap-4' }, [
      e('div', { className: 'p-4 bg-white rounded shadow', key: 'settings' }, [
        e('h2', { key: 'settings-h', className: 'font-semibold mb-2' }, 'Settings'),
        e('div', { className: 'space-y-2' }, [
          e('input', { key: 'base', className: 'w-full border p-2', placeholder: 'Base URL', value: baseUrl, onChange: ev => setBaseUrl(ev.target.value) }),
          e('input', { key: 'key', className: 'w-full border p-2', placeholder: 'API Key', value: apiKey, onChange: ev => setApiKey(ev.target.value) }),
          e('div', { className: 'grid grid-cols-2 gap-2' }, [
            e('input', { key: 'company', className: 'w-full border p-2', placeholder: 'Company ID', value: companyId, onChange: ev => setCompanyId(ev.target.value) }),
            e('input', { key: 'source', className: 'w-full border p-2', placeholder: 'Source', value: source, onChange: ev => setSource(ev.target.value) }),
          ]),
          e('button', { key: 'use-origin', type: 'button', onClick: () => setBaseUrl(window.location.origin), className: 'px-3 py-2 bg-gray-200 rounded' }, 'Use current origin')
        ])
      ]),
      e('div', { className: 'p-4 bg-white rounded shadow', key: 'analyze' }, [
        e('h2', { key: 'analyze-h', className: 'font-semibold mb-2' }, 'Analyze Text'),
        e('form', { onSubmit: onAnalyze, className: 'space-y-2' }, [
          e('textarea', { className: 'w-full border p-2 h-28', value: text, onChange: ev => setText(ev.target.value) }),
          e('div', { className: 'flex items-center gap-2' }, [
            e('label', { className: 'text-sm text-gray-600' }, 'Language'),
            e('select', { className: 'border p-2', value: langHint, onChange: ev => setLangHint(ev.target.value) }, [
              e('option', { key: 'auto', value: '' }, 'Auto-detect'),
              e('option', { key: 'en', value: 'en' }, 'English'),
              e('option', { key: 'fr', value: 'fr' }, 'French'),
              e('option', { key: 'sw', value: 'sw' }, 'Swahili'),
              e('option', { key: 'rw', value: 'rw' }, 'Kinyarwanda'),
            ])
          ]),
          e('div', { className: 'flex gap-2' }, [
            e('button', { key: 'btn-analyze', type: 'submit', disabled: loading.analyze, className: 'px-3 py-2 rounded text-white ' + (loading.analyze ? 'bg-blue-300' : 'bg-blue-600') }, loading.analyze ? 'Analyzing…' : 'Analyze'),
            e('button', { key: 'btn-submit', type: 'button', onClick: onSubmitFeedback, disabled: loading.fb, className: 'px-3 py-2 rounded text-white ' + (loading.fb ? 'bg-amber-300' : 'bg-amber-600') }, loading.fb ? 'Submitting…' : 'Submit Feedback'),
            e('button', { key: 'btn-ws', type: 'button', onClick: connectWS, disabled: wsConnected, className: 'px-3 py-2 rounded text-white ' + (wsConnected ? 'bg-emerald-300' : 'bg-emerald-600') }, wsConnected ? 'WS Connected' : 'Stream Once')
          ])
        ]),
      ])
    ]),

    e('div', { className: 'grid grid-cols-1 md:grid-cols-2 gap-4' }, [
      e('div', { className: 'p-4 bg-white rounded shadow', key: 'result' }, [
        e('h3', { key: 'result-h', className: 'font-semibold' }, 'Result'),
        result ? e('div', { className: 'mt-2 space-y-3' }, [
          e('div', { key: 'lang', className: 'text-sm text-gray-600 flex items-center gap-2' }, [
            `Language: ${result.language || 'n/a'}`,
            result.polarity ? e('span', { className: 'px-2 py-0.5 rounded text-white text-xs ' + ((result.polarity.negative||0) > (result.polarity.positive||0) ? 'bg-rose-600' : (result.polarity.positive||0) > (result.polarity.negative||0) ? 'bg-emerald-600' : 'bg-gray-600') }, (
              (result.polarity.negative||0) > (result.polarity.positive||0) ? 'Negative' : (result.polarity.positive||0) > (result.polarity.negative||0) ? 'Positive' : 'Neutral'
            )) : null
          ]),
          result.polarity ? e('div', { key: 'pol' }, [ e('h4', { className: 'font-medium mb-1' }, 'Polarity'), e(PolarityBar, { polarity: result.polarity }) ]) : null,
          e('div', { key: 'bars' }, [ e('h4', { className: 'font-medium mb-1' }, 'Emotions'), e(EmotionBars, { emotions: result.emotions }) ]),
          e('div', { key: 'tox' }, [ e('h4', { className: 'font-medium mb-1' }, 'Toxicity (top 8)'), e(ToxicityList, { toxicity: result.toxicity }) ]),
          typeof result.sarcasm_likelihood === 'number' ? e('div', { key: 'sarc_like', className: 'text-sm' }, `Sarcasm likelihood: ${(result.sarcasm_likelihood*100).toFixed(1)}%`) : null,
          result.sarcasm && Object.keys(result.sarcasm).length ? e('div', { key: 'sarc' }, [ e('h4', { className: 'font-medium mb-1' }, 'Sarcasm Signals'), e(SarcasmList, { sarcasm: result.sarcasm }) ]) : null,
          result.aspects && result.aspects.length ? e('div', { key: 'aspects' }, [ e('h4', { className: 'font-medium mb-1' }, 'Aspects'), e(AspectList, { aspects: result.aspects }) ]) : null,
          e('details', { key: 'raw' }, [ e('summary', null, 'Raw JSON'), e('pre', { className: 'mt-2 bg-gray-50 p-2 overflow-auto text-sm' }, JSON.stringify(result, null, 2)) ])
        ]) : e('p', null, 'No result yet')
      ]),
      e('div', { className: 'p-4 bg-white rounded shadow', key: 'stream' }, [
        e('h3', { key: 'stream-h', className: 'font-semibold' }, 'Live Stream (last 50)'),
        e('div', { className: 'mt-2 space-y-2 max-h-80 overflow-auto text-sm' }, wsMessages.map((m, idx) => e('pre', { key: idx, className: 'bg-gray-50 p-2' }, JSON.stringify(m, null, 2))))
      ])
    ]),

    // Advanced actions row
    e('div', { className: 'grid grid-cols-1 md:grid-cols-2 gap-4' }, [
      e('div', { className: 'p-4 bg-white rounded shadow', key: 'xai' }, [
        e('h3', { key: 'xai-h', className: 'font-semibold mb-2' }, 'Explain (XAI)'),
        e('div', { className: 'flex gap-2' }, [
          e('button', { key: 'btn-explain', type: 'button', onClick: onExplain, disabled: loading.explain, className: 'px-3 py-2 rounded text-white ' + (loading.explain ? 'bg-indigo-300' : 'bg-indigo-600') }, loading.explain ? 'Explaining…' : 'Explain')
        ]),
        explain ? e('div', { className: 'mt-3 space-y-2' }, [
          e('div', { key: 'target', className: 'text-sm text-gray-600' }, `Target emotion: ${explain.target_emotion || 'n/a'}`),
          e('div', { key: 'tokens' }, [
            e('h4', { className: 'font-medium mb-1' }, 'Top tokens'),
            e('ul', { className: 'list-disc pl-5 text-sm' }, (explain.tokens||[]).map((t, i) => e('li', { key: i }, `${t.token}: ${(t.weight*100).toFixed(1)}%`)))
          ]),
          e('details', { key: 'raw' }, [ e('summary', null, 'Raw JSON'), e('pre', { className: 'bg-gray-50 p-2 overflow-auto text-sm' }, JSON.stringify(explain, null, 2)) ])
        ]) : null
      ]),

      e('div', { className: 'p-4 bg-white rounded shadow', key: 'zeroshot' }, [
        e('h3', { key: 'zs-h', className: 'font-semibold mb-2' }, 'Zero-shot Classification'),
        e('div', { className: 'space-y-2' }, [
          e('input', { key: 'zslabels', className: 'w-full border p-2', placeholder: 'Labels (comma separated)', value: zsLabels, onChange: ev => setZsLabels(ev.target.value) }),
          e('label', { key: 'zsmulti', className: 'flex items-center gap-2 text-sm' }, [
            e('input', { type: 'checkbox', checked: zsMulti, onChange: ev => setZsMulti(ev.target.checked) }),
            e('span', null, 'Multi-label')
          ]),
          e('button', { key: 'btn-zs', type: 'button', onClick: onZeroShot, disabled: loading.zs, className: 'px-3 py-2 rounded text-white ' + (loading.zs ? 'bg-purple-300' : 'bg-purple-600') }, loading.zs ? 'Classifying…' : 'Classify')
        ]),
        zsResult ? e('pre', { className: 'mt-3 bg-gray-50 p-2 overflow-auto text-sm' }, JSON.stringify(zsResult, null, 2)) : null
      ])
    ]),

    e('div', { className: 'grid grid-cols-1 md:grid-cols-2 gap-4' }, [
      e('div', { className: 'p-4 bg-white rounded shadow', key: 'moderation' }, [
        e('h3', { key: 'mod-h', className: 'font-semibold mb-2' }, 'Moderation'),
        e('div', { className: 'flex items-center gap-2' }, [
          e('label', { key: 'thlbl', className: 'text-sm' }, 'Threshold'),
          e('input', { key: 'th', type: 'number', min: 0, max: 1, step: 0.05, className: 'border p-2 w-28', value: modThreshold, onChange: ev => setModThreshold(ev.target.value) }),
          e('button', { key: 'btn-mod', type: 'button', onClick: onModerate, disabled: loading.mod, className: 'px-3 py-2 rounded text-white ' + (loading.mod ? 'bg-rose-300' : 'bg-rose-600') }, loading.mod ? 'Checking…' : 'Check')
        ]),
        modResult ? e('pre', { className: 'mt-3 bg-gray-50 p-2 overflow-auto text-sm' }, JSON.stringify(modResult, null, 2)) : null
      ]),

      e('div', { className: 'p-4 bg-white rounded shadow', key: 'domain' }, [
        e('h3', { key: 'domain-h', className: 'font-semibold mb-2' }, 'Domain Analysis'),
        e('div', { className: 'flex items-center gap-2' }, [
          e('select', { key: 'domain-sel', className: 'border p-2', value: domain, onChange: ev => setDomain(ev.target.value) }, [
            e('option', { key: 'support', value: 'support' }, 'Support'),
            e('option', { key: 'reviews', value: 'reviews' }, 'Reviews'),
            e('option', { key: 'mental-health', value: 'mental-health' }, 'Mental Health'),
            e('option', { key: 'social', value: 'social' }, 'Social'),
          ]),
          e('button', { key: 'btn-domain', type: 'button', onClick: onDomain, disabled: loading.domain, className: 'px-3 py-2 rounded text-white ' + (loading.domain ? 'bg-teal-300' : 'bg-teal-600') }, loading.domain ? 'Running…' : 'Run')
        ]),
        domainResult ? e('pre', { className: 'mt-3 bg-gray-50 p-2 overflow-auto text-sm' }, JSON.stringify(domainResult, null, 2)) : null
      ])
    ]),

    // Analytics section
    e('div', { className: 'grid grid-cols-1 md:grid-cols-2 gap-4' }, [
      e('div', { className: 'p-4 bg-white rounded shadow', key: 'analytics' }, [
        e('h3', { className: 'font-semibold mb-2' }, 'Analytics Overview'),
        e('div', { className: 'flex items-center gap-2 mb-2' }, [
          e('label', { className: 'text-sm text-gray-600' }, 'Days'),
          e('input', { type: 'number', min: 1, max: 365, className: 'border p-2 w-24', value: analyticsDays, onChange: ev => setAnalyticsDays(Number(ev.target.value||30)) }),
          e('button', { type: 'button', onClick: onLoadAnalytics, disabled: loading.analytics, className: 'px-3 py-2 rounded text-white ' + (loading.analytics ? 'bg-gray-300' : 'bg-gray-700') }, loading.analytics ? 'Loading…' : 'Load')
        ]),
        analytics ? e('div', { className: 'space-y-3' }, [
          e('div', null, [ e('h4', { className: 'font-medium mb-1' }, `Trend (${analytics.trend})`), e(SatisfactionTrend, { series: analytics.series }) ]),
          e('div', null, [ e('h4', { className: 'font-medium mb-1' }, 'Emotion Distribution'), e(EmotionDistributionBars, { dist: analytics.emotion_distribution }) ])
        ]) : e('p', { className: 'text-sm text-gray-500' }, 'No analytics loaded')
      ]),
      e('div', { className: 'p-4 bg-white rounded shadow', key: 'insights' }, [
        e('h3', { className: 'font-semibold mb-2' }, 'Actionable Insights'),
        analytics && analytics.suggestions && analytics.suggestions.length ?
          e('ul', { className: 'list-disc pl-5 text-sm' }, analytics.suggestions.map((s, i) => e('li', { key: i }, `${s.text} (${s.count})`))) :
          e('p', { className: 'text-sm text-gray-500' }, 'No suggestions yet')
      ])
    ])
  ]);
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(e(App));
