import os
import json
import time
from typing import Any, Dict, List, Optional

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # noqa

REDIS_URL = os.environ.get("REDIS_URL")

class Store:
    def __init__(self) -> None:
        self._mem: Dict[str, List[Dict[str, Any]] ] = {}
        self._r = None
        if REDIS_URL and redis is not None:
            self._r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    def append_timeline(self, conv_id: str, payload: Dict[str, Any]) -> None:
        item = {"ts": time.time(), **payload}
        if self._r is not None:
            self._r.rpush(self._key(conv_id), json.dumps(item))
        else:
            self._mem.setdefault(conv_id, []).append(item)

    def get_timeline(self, conv_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        if self._r is not None:
            key = self._key(conv_id)
            length = self._r.llen(key)
            start = max(0, length - limit)
            raw = self._r.lrange(key, start, -1)
            return [json.loads(x) for x in raw]
        return self._mem.get(conv_id, [])[-limit:]

    def _key(self, conv_id: str) -> str:
        return f"timeline:{conv_id}"

store = Store()
