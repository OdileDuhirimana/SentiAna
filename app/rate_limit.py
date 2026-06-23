import time
from collections import deque, defaultdict
from typing import Deque, Dict, Tuple
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

RateKey = Tuple[str, str]  # (client_ip, route_path)

class SlidingWindowRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, requests:int=60, window_seconds:int=60):
        super().__init__(app)
        self.requests = requests
        self.window = window_seconds
        self.buckets: Dict[RateKey, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_ip = (request.headers.get("x-forwarded-for") or request.client.host or "unknown").split(",")[0].strip()
        key: RateKey = (client_ip, request.url.path)
        now = time.time()
        q = self.buckets[key]
        # evict old timestamps
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.requests:
            return Response("Rate limit exceeded", status_code=HTTP_429_TOO_MANY_REQUESTS)
        q.append(now)
        return await call_next(request)
