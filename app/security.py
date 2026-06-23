import os
import time
import jwt
from fastapi import Depends, HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED

API_KEY = os.environ.get("SENTIMENTSCOPE_API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_ALG = os.environ.get("JWT_ALG", "HS256")
bearer_scheme = HTTPBearer(auto_error=False)

def get_api_key(api_key: str | None = Security(api_key_header)) -> None:
    if API_KEY is None:
        return None
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    return None

def create_token(sub: str, ttl_seconds: int = 3600) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET not configured")
    now = int(time.time())
    payload = {"sub": sub, "iat": now, "exp": now + ttl_seconds}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def verify_token(token: str) -> dict:
    if not JWT_SECRET:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception as e:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token") from e

def get_auth(request: Request, api_key: str | None = Security(api_key_header), creds: HTTPAuthorizationCredentials | None = Security(bearer_scheme)) -> None:
    # Accept either API key (if configured) or Bearer JWT (if configured)
    if API_KEY is None and JWT_SECRET is None:
        return None
    # Check API key first if provided
    provided_key = api_key
    if provided_key and API_KEY and provided_key == API_KEY:
        return None
    # Then check bearer JWT
    if JWT_SECRET and creds and creds.scheme.lower() == "bearer" and creds.credentials:
        verify_token(creds.credentials)
        return None
    raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Unauthorized")
