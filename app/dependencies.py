"""
Authentication, rate limiting and authorization checks that run
before a protected endpoint's own code. In FastAPI these are called
"dependencies" rather than middleware, but they do the same job:
intercept the request, check something, and either let it through
or reject it.

The order they run in is: authenticate (401) -> rate limit (429)
-> check scope (403).
"""

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey
from app.rate_limit import check_rate_limit
from app.security import split_key, verify_secret

bearer_scheme = HTTPBearer()


def get_current_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> ApiKey:
    """
    AUTHENTICATION: proves the key is genuine and currently
    active. Says nothing about what it's allowed to do.
    """
    presented_key = credentials.credentials

    parsed = split_key(presented_key)
    if parsed is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    key_prefix, secret = parsed

    api_key = db.query(ApiKey).filter(ApiKey.key_prefix == key_prefix).first()

    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if api_key.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not verify_secret(secret, api_key.key_hash):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key


def get_rate_limited_key(current_key: ApiKey = Depends(get_current_key)) -> ApiKey:
    """
    RATE LIMITING: runs only after authentication succeeds, so we
    know which key to count the request against. Counts per key id.
    """
    check_rate_limit(str(current_key.id))
    return current_key


def require_scope(required_scope: str):
    """
    AUTHORIZATION: a genuine key isn't automatically allowed to do
    everything -- this checks it's specifically allowed to do
    *this*. A dependency factory: see our earlier discussion of why
    there's an outer and an inner function.

    It depends on get_rate_limited_key (not get_current_key), so
    every scope-protected endpoint is rate limited automatically.
    """

    def check_scope(current_key: ApiKey = Depends(get_rate_limited_key)) -> ApiKey:
        if required_scope not in current_key.scopes:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_key

    return check_scope