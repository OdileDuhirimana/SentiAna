from functools import lru_cache
from typing import Dict, List, Protocol
from langdetect import detect
import yake
import re
import os
try:
    from transformers import pipeline  # type: ignore
    _HF_AVAILABLE = True
except ImportError:
    pipeline = None  # type: ignore[assignment]
    _HF_AVAILABLE = False
try:
    import redis  # type: ignore
except Exception:
    redis = None

_DEMO_MODE = os.environ.get("DEMO_MODE", "0") in {"1", "true", "True"}

SUPPORTED_LANGS = {"en", "fr", "rw", "sw"}

_WORD_RE = re.compile(r"[^\w\s']")  # strip punctuation for word matching


class _NLPEngineProto(Protocol):
    def analyze(self, text: str, lang_hint: str | None = None) -> Dict: ...
    def get_models(self) -> Dict: ...
    def reset(self) -> Dict: ...

class NLPEngine:
    def __init__(self) -> None:
        if not _HF_AVAILABLE:
            raise RuntimeError(
                "transformers is not installed. Set DEMO_MODE=1 to run without ML models."
            )
        self._emotion_model = os.environ.get("EMOTION_MODEL", "SamLowe/roberta-base-go_emotions")
        self._toxicity_model = os.environ.get("TOXICITY_MODEL", "unitary/unbiased-toxic-roberta")
        self._sarcasm_model = os.environ.get("SARCASM_MODEL", "cardiffnlp/twitter-roberta-base-sarcasm")
        self._emotion2_model = os.environ.get("SECOND_EMOTION_MODEL")  # optional
        self._use_multilingual_polarity = os.environ.get("USE_MULTILINGUAL_POLARITY", "1") not in {"0", "false", "False"}
        try:
            self._min_emotion_score = float(os.environ.get("EMOTION_MIN_SCORE", "0.35"))
        except Exception:
            self._min_emotion_score = 0.35

        self._emotion = pipeline(
            "text-classification",
            model=self._emotion_model,
            top_k=None,
            function_to_apply="sigmoid",
            truncation=True,
        )
        self._emotion2 = None
        if self._emotion2_model:
            try:
                self._emotion2 = pipeline(
                    "text-classification",
                    model=self._emotion2_model,
                    top_k=None,
                    function_to_apply="sigmoid",
                    truncation=True,
                )
            except Exception:
                self._emotion2 = None
        self._toxicity = pipeline(
            "text-classification",
            model=self._toxicity_model,
            top_k=None,
            truncation=True,
        )
        # Sarcasm pipeline may be gated/private; do not fail startup if unavailable
        self._sarcasm = None
        try:
            self._sarcasm = pipeline(
                "text-classification",
                model=self._sarcasm_model,
                top_k=None,
                truncation=True,
            )
        except Exception:
            self._sarcasm = None
        self._kw_extractor = yake.KeywordExtractor(lan="en", n=1, top=5)
        # Translation pipelines for basic multilingual support
        # Only initialize when needed to keep startup time reasonable
        self._translator_fr_en = None
        self._translator_sw_en = None
        self._translator_rw_en = None
        self._translator_rw_en_nllb = None
        self._nllb_src = "kin_Kinyarwanda"
        self._nllb_tgt = "eng_Latn"
        # Optional Redis cache for analysis results
        self._rc = None
        red_url = os.environ.get("REDIS_URL")
        if red_url and redis is not None:
            try:
                self._rc = redis.Redis.from_url(red_url, decode_responses=True)
            except Exception:
                self._rc = None

    def _detect_lang(self, text: str, hint: str | None = None) -> str:
        if hint and hint in SUPPORTED_LANGS:
            return hint
        try:
            lang = detect(text)
            # Map langdetect codes to our set
            if lang in {"en", "fr", "sw"}:
                return lang
            # Kinyarwanda often detected as 'rw'
            if lang == "rw":
                return "rw"
        except Exception:
            pass
        return "en"

    def _translate_to_en(self, text: str, source_lang: str) -> str:
        try:
            if source_lang == "fr":
                if self._translator_fr_en is None:
                    self._translator_fr_en = pipeline("translation", model="Helsinki-NLP/opus-mt-fr-en")
                return self._translator_fr_en(text)[0]["translation_text"]
            if source_lang == "sw":
                if self._translator_sw_en is None:
                    self._translator_sw_en = pipeline("translation", model="Helsinki-NLP/opus-mt-sw-en")
                return self._translator_sw_en(text)[0]["translation_text"]
            if source_lang == "rw":
                # Prefer NLLB if available for better quality, fallback to Marian
                if self._translator_rw_en_nllb is None:
                    try:
                        # NLLB requires src/tgt language codes
                        self._translator_rw_en_nllb = pipeline(
                            "translation",
                            model="facebook/nllb-200-distilled-600M",
                            src_lang=self._nllb_src,
                            tgt_lang=self._nllb_tgt,
                        )
                    except Exception:
                        self._translator_rw_en_nllb = None
                if self._translator_rw_en_nllb is not None:
                    out = self._translator_rw_en_nllb(text)
                    # NLLB output uses 'translation_text' like others
                    return out[0].get("translation_text") or out[0].get("generated_text") or text
                if self._translator_rw_en is None:
                    try:
                        self._translator_rw_en = pipeline("translation", model="Helsinki-NLP/opus-mt-rw-en")
                    except Exception:
                        self._translator_rw_en = pipeline("translation", model="Helsinki-NLP/opus-mt-tc-big-rw-en")
                return self._translator_rw_en(text)[0]["translation_text"]
        except Exception:
            # Fallback to original text if translation fails
            return text
        return text

    @lru_cache(maxsize=1024)
    def _analyze_cached(self, text: str) -> Dict:
        emotions_raw = self._emotion(text)[0]
        emotions_map = {e["label"]: float(e["score"]) for e in emotions_raw}
        # Optional second model ensemble averaging
        if self._emotion2 is not None:
            try:
                e2 = self._emotion2(text)[0]
                for item in e2:
                    lbl = item["label"]
                    s = float(item["score"])
                    if lbl in emotions_map:
                        emotions_map[lbl] = (emotions_map[lbl] + s) / 2.0
                    else:
                        emotions_map[lbl] = s
            except Exception:
                pass
        emotions = sorted(
            [{"label": k, "score": v} for k, v in emotions_map.items()],
            key=lambda x: x["score"],
            reverse=True,
        )
        # Filter out low-confidence emotions
        emotions = [e for e in emotions if e["score"] >= self._min_emotion_score]
        tox_raw = self._toxicity(text)[0]
        toxicity = {t["label"].lower(): float(t["score"]) for t in tox_raw}
        if self._sarcasm is not None:
            try:
                sarc_raw = self._sarcasm(text)[0]
                sarcasm = {s["label"].lower(): float(s["score"]) for s in sarc_raw}
            except Exception:
                sarcasm = {}
        else:
            sarcasm = {}
        # Simple aspect extraction with YAKE keywords as aspects
        kws = self._kw_extractor.extract_keywords(text)
        aspects = [{"aspect": k, "sentiment": None} for k, _ in kws]
        # Coarse polarity from emotions for aspect sentiment
        pos_keys = {"joy","admiration","excitement","amusement","gratitude","pride","relief","love","optimism"}
        neg_keys = {"sadness","anger","disappointment","annoyance","disgust","embarrassment","fear","grief","remorse"}
        emo_map = {e["label"]: float(e["score"]) for e in emotions}
        pos = sum(emo_map.get(k, 0.0) for k in pos_keys)
        neg = sum(emo_map.get(k, 0.0) for k in neg_keys)
        pol = pos - neg
        if aspects:
            sentiment = "positive" if pol > 0.1 else ("negative" if pol < -0.1 else "mixed")
            for a in aspects:
                a["sentiment"] = sentiment
        # Provide a single sarcasm likelihood score (max of labels if any)
        sarc_like = 0.0
        if sarcasm:
            try:
                sarc_like = float(max(sarcasm.values()))
            except Exception:
                sarc_like = 0.0
        return {"emotions": emotions, "toxicity": toxicity, "sarcasm": sarcasm, "sarcasm_likelihood": sarc_like, "aspects": aspects}

    def analyze(self, text: str, lang_hint: str | None = None) -> Dict:
        language = self._detect_lang(text, hint=lang_hint)
        text_for_analysis = text
        if language in {"fr", "sw", "rw"}:
            text_for_analysis = self._translate_to_en(text, language)
        # Optional multilingual polarity pipeline
        polarity = {}
        if self._use_multilingual_polarity:
            try:
                if not hasattr(self, "_polarity") or self._polarity is None:
                    self._polarity = pipeline(
                        "text-classification",
                        model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
                        top_k=None,
                        truncation=True,
                    )
                pol_raw = self._polarity(text if language != "en" else text_for_analysis)[0]
                # Map labels to consistent order
                pol_map = {p["label"].lower(): float(p["score"]) for p in pol_raw}
                polarity = {
                    "negative": pol_map.get("negative", 0.0),
                    "neutral": pol_map.get("neutral", 0.0),
                    "positive": pol_map.get("positive", 0.0),
                }
            except Exception:
                polarity = {}
        # Try Redis cache first
        if self._rc is not None:
            key = f"ana:{text_for_analysis}"
            try:
                cached = self._rc.get(key)
                if cached:
                    import json
                    result = json.loads(cached)
                else:
                    result = self._analyze_cached(text_for_analysis)
                    self._rc.setex(key, 3600, __import__("json").dumps(result))
            except Exception:
                result = self._analyze_cached(text_for_analysis)
        else:
            result = self._analyze_cached(text_for_analysis)
        result["language"] = language
        result["text_en"] = text_for_analysis
        if polarity:
            result["polarity"] = polarity
        return result

class LazyNLPEngine:
    def __init__(self) -> None:
        self._engine: NLPEngine | None = None

    def _get_engine(self) -> NLPEngine:
        if self._engine is None:
            self._engine = NLPEngine()
        return self._engine

    def analyze(self, text: str, lang_hint: str | None = None) -> Dict:
        return self._get_engine().analyze(text, lang_hint=lang_hint)

    def __getattr__(self, name):
        return getattr(self._get_engine(), name)

    def get_models(self) -> Dict:
        engine = self._get_engine()
        return {
            "emotion_model": engine._emotion_model,
            "second_emotion_model": engine._emotion2_model,
            "toxicity_model": engine._toxicity_model,
            "sarcasm_model": engine._sarcasm_model,
        }

    def reset(self) -> Dict:
        self._engine = NLPEngine()
        try:
            self._engine._analyze_cached.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            pass
        return self.get_models()


class DemoNLPEngine:
    """Lightweight demo engine — no transformer models, no PyTorch.
    Uses YAKE for keywords and langdetect for language detection;
    emotion/toxicity scores are rule-based heuristics."""

    _POS = {"good","great","excellent","love","happy","wonderful","amazing","best","thank","awesome","fantastic","brilliant"}
    _NEG = {"bad","terrible","hate","awful","worst","horrible","disappointing","poor","broken","failed"}
    _TOX = {"hate","kill","die","stupid","idiot","moron","loser","dumb","useless","worthless"}

    def __init__(self) -> None:
        self._kw_extractor = yake.KeywordExtractor(lan="en", n=1, top=5)
        self._emotion_model = "demo"
        self._emotion2_model = None
        self._toxicity_model = "demo"
        self._sarcasm_model = "demo"
        self._engine = self  # LazyNLPEngine compat

    def analyze(self, text: str, lang_hint: str | None = None) -> Dict:
        try:
            raw_lang = detect(text)
            language = raw_lang if raw_lang in SUPPORTED_LANGS else "en"
        except Exception:
            language = "en"
        if lang_hint and lang_hint in SUPPORTED_LANGS:
            language = lang_hint

        cleaned = _WORD_RE.sub("", text.lower())
        words = cleaned.split()
        word_set = set(words)
        total = max(len(words), 1)
        pos = len(word_set & self._POS)
        neg = len(word_set & self._NEG)
        tox = len(word_set & self._TOX)

        if pos > neg:
            score_a = round(min(0.93, 0.55 + pos / total * 2), 3)
            score_b = round(min(0.72, 0.35 + pos / total), 3)
            emotions: List[Dict] = [{"label": "joy", "score": score_a}, {"label": "admiration", "score": score_b}]
            pol = "positive"
        elif neg > 0:
            score_a = round(min(0.88, 0.50 + neg / total * 2), 3)
            score_b = round(min(0.65, 0.30 + neg / total), 3)
            emotions = [{"label": "disappointment", "score": score_a}, {"label": "sadness", "score": score_b}]
            pol = "negative"
        else:
            emotions = [{"label": "neutral", "score": 0.65}, {"label": "approval", "score": 0.32}]
            pol = "mixed"

        toxic_score = round(min(0.95, 0.04 + tox / total * 3), 3)
        try:
            kws = self._kw_extractor.extract_keywords(text)
            aspects = [{"aspect": k, "sentiment": pol} for k, _ in kws]
        except Exception:
            aspects = []

        pos_pol = round(min(1.0, max(0.0, 0.5 + (pos - neg) / total)), 3)
        neg_pol = round(min(1.0, max(0.0, 0.5 + (neg - pos) / total)), 3)
        neutral_pol = round(max(0.0, 1.0 - pos_pol - neg_pol), 3)
        return {
            "emotions": emotions,
            "toxicity": {"toxic": toxic_score, "non-toxic": round(1.0 - toxic_score, 3)},
            "sarcasm": {},
            "sarcasm_likelihood": 0.0,
            "aspects": aspects,
            "language": language,
            "text_en": text,
            "polarity": {"positive": pos_pol, "neutral": neutral_pol, "negative": neg_pol},
            "demo": True,
        }

    def get_models(self) -> Dict:
        return {"emotion_model": "demo", "second_emotion_model": None, "toxicity_model": "demo", "sarcasm_model": "demo"}

    def reset(self) -> Dict:
        return self.get_models()

    def __getattr__(self, name: str):
        raise AttributeError(f"DemoNLPEngine has no attribute '{name}'")


engine: _NLPEngineProto = DemoNLPEngine() if _DEMO_MODE else LazyNLPEngine()


def reload_models(emotion_model: str | None = None, toxicity_model: str | None = None, sarcasm_model: str | None = None) -> Dict:
    global engine
    if _DEMO_MODE:
        # Model config is irrelevant in demo mode; report current state
        return engine.get_models()
    if emotion_model:
        os.environ["EMOTION_MODEL"] = emotion_model
    if toxicity_model:
        os.environ["TOXICITY_MODEL"] = toxicity_model
    if sarcasm_model:
        os.environ["SARCASM_MODEL"] = sarcasm_model
    # Rebuild the lazy engine so next analyze() picks up new env vars
    engine = LazyNLPEngine()
    return engine.reset()
