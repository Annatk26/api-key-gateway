"""
The authentication check that runs before a protected endpoint's
own code. In FastAPI this is called a "dependency" rather than
middleware, but it does the same job: intercept the request,
check the key, and either let it through or reject it.
"""

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey
from app.security import split_key, verify_secret

# HTTPBearer is a scheme FastAPI recognises and knows how to
# describe in its auto-generated docs -- this is what makes the
# lock icon and "Authorize" button appear in /docs, instead of a
# plain, easy-to-miss text field. It also does the "Bearer "
# prefix parsing for us, so we no longer do that by hand below.
bearer_scheme = HTTPBearer()


def get_current_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> ApiKey:
    """
    Reads the bearer token, verifies the key against the
    database, and returns the matching ApiKey row if valid.

    Raises a 401 error for every kind of failure -- malformed
    key, unknown prefix, wrong secret, or a revoked key.
    Deliberately the same error for all of these: telling an
    attacker *why* a key failed (e.g. "that prefix doesn't exist"
    vs "wrong secret") would help them narrow down guesses.
    """
    presented_key = credentials.credentials

    parsed = split_key(presented_key)
    if parsed is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    key_prefix, secret = parsed

    # This is the fast lookup: find the ONE row with this prefix,
    # rather than hashing and comparing against every row.
    api_key = db.query(ApiKey).filter(ApiKey.key_prefix == key_prefix).first()

    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if api_key.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not verify_secret(secret, api_key.key_hash):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key