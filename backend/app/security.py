"""Authentication for the API: one account, set by environment variables.

    ADMIN_USERNAME   default "admin"
    ADMIN_PASSWORD   required when APP_ENV=production; in development a random one is made
                     and printed once at startup if unset
    SECRET_KEY       signs login tokens; same rule as the password
    TOKEN_MINUTES    token lifetime, default 480
    MESSAGES_PER_MINUTE   limit on tutor messages, default 30

POST /auth/login returns a token. Every route except /health and /auth/login needs it.
Generate a password with:  python -c "import secrets; print(secrets.token_urlsafe(16))"
"""
import hmac
import logging
import os
import secrets
import time
from collections import defaultdict, deque

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

log = logging.getLogger("tutor.security")
ALGORITHM = "HS256"
_generated: dict[str, str] = {}


def _setting(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    if os.environ.get("APP_ENV") == "production":
        raise RuntimeError(f"{name} must be set when APP_ENV=production")
    if name not in _generated:  # development convenience: a random value for this run only
        _generated[name] = secrets.token_urlsafe(16)
        if name == "ADMIN_PASSWORD":
            log.warning("ADMIN_PASSWORD is not set. Password for this run: %s", _generated[name])
        else:
            log.warning("%s is not set; using a temporary value for this run.", name)
    return _generated[name]


def username() -> str:
    return os.environ.get("ADMIN_USERNAME", "admin")


def check_config() -> None:
    """Fail at startup, not on the first request, if production is misconfigured."""
    _setting("ADMIN_PASSWORD")
    _setting("SECRET_KEY")


def check_login(user: str, password: str) -> bool:
    """Compares both values in constant time so timing does not reveal which one was wrong."""
    ok_user = hmac.compare_digest(user.encode(), username().encode())
    ok_pass = hmac.compare_digest(password.encode(), _setting("ADMIN_PASSWORD").encode())
    return ok_user and ok_pass


def make_token() -> str:
    now = int(time.time())
    minutes = int(os.environ.get("TOKEN_MINUTES", "480"))
    return jwt.encode({"sub": username(), "iat": now, "exp": now + minutes * 60}, _setting("SECRET_KEY"), algorithm=ALGORITHM)


_bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    denied = HTTPException(401, "Sign in required", headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise denied
    try:
        claims = jwt.decode(creds.credentials, _setting("SECRET_KEY"), algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        raise denied
    return claims["sub"]


# ── Rate limiting (in memory, per process) ───────────────────────────────────
class RateLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)

    def hit(self, key: str, limit: int, window: int = 60) -> None:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(429, "Too many requests. Please wait a minute.", headers={"Retry-After": str(window)})
        q.append(now)

    def reset(self) -> None:
        self._hits.clear()


limiter = RateLimiter()


def limit_login(request: Request) -> None:
    """Slows password guessing: 10 attempts per minute per address."""
    limiter.hit(f"login:{request.client.host if request.client else '?'}", limit=10)


def limit_messages(user: str) -> None:
    """Protects the model from being hammered."""
    limiter.hit(f"msg:{user}", limit=int(os.environ.get("MESSAGES_PER_MINUTE", "30")))
