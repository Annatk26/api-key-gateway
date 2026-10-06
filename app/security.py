"""
Handles generating new API keys and verifying keys presented on
incoming requests.

Core idea: we never store the real key. We store a hash of it
(one-way, can't be reversed) plus a plain-text prefix used to
find the right row quickly. See SETUP.md / our discussion for the
full reasoning.
"""

import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import KEY_PREFIX_LABEL

# PasswordHasher implements Argon2, the modern standard for
# hashing secrets. It's deliberately slow -- that's a feature,
# not a bug, since it makes guessing keys by brute force
# impractical.
_hasher = PasswordHasher()


def generate_api_key() -> tuple[str, str, str]:
    """
    Creates a brand new API key.

    Returns a tuple of:
      - full_key: the real key, shown to the user ONCE, never
        stored anywhere
      - key_prefix: the searchable, non-secret part, stored in
        plain text in the database
      - key_hash: the hash of the secret part, stored in the
        database instead of the real key
    """
    # A short random identifier for this key, safe to store and
    # display in plain text -- this is what makes lookups fast.
    prefix_id = secrets.token_hex(6)  # 12 hex characters
    key_prefix = f"{KEY_PREFIX_LABEL}_{prefix_id}"

    # The actual secret. token_urlsafe generates a long random
    # string safe to use in URLs and headers.
    secret = secrets.token_urlsafe(32)

    # "." separates the two parts -- chosen because it never
    # appears in either the hex prefix or a urlsafe secret, so
    # splitting the key back apart later is unambiguous.
    full_key = f"{key_prefix}.{secret}"

    key_hash = _hasher.hash(secret)

    return full_key, key_prefix, key_hash


def split_key(full_key: str) -> tuple[str, str] | None:
    """
    Splits a presented key back into (key_prefix, secret).
    Returns None if the key doesn't look like a valid shape at
    all -- e.g. missing the separator entirely.
    """
    prefix_part, separator, secret_part = full_key.partition(".")
    if not separator:
        return None
    return prefix_part, secret_part


def verify_secret(secret: str, key_hash: str) -> bool:
    """
    Checks a presented secret against the stored hash.
    Returns True only if they match.
    """
    try:
        _hasher.verify(key_hash, secret)
        return True
    except VerifyMismatchError:
        return False