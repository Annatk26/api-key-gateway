"""
Fixed-window rate limiting, backed by Redis.

Idea: split time into windows (say, 60 seconds each). Every key gets
a counter per window. Each request adds 1 to its key's counter for
the current window, and once the counter passes the limit, further
requests in that window are rejected until the next window starts.
"""

import logging
import time

import redis
from fastapi import HTTPException

from app.config import REDIS_URL, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS

logger = logging.getLogger(__name__)

# The timeouts matter: if Redis is down or slow, we want to find out
# within a second, not leave every request hanging.
redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def check_rate_limit(identifier: str) -> None:
    """
    Counts one request for this identifier and raises a 429 error
    if it has gone over the limit for the current window.
    """
    now = int(time.time())

    # Which window are we in? Integer division groups every second
    # of a 60-second span into the same number, e.g. all of
    # 12:00:00-12:00:59 share one window number, and 12:01:00 starts
    # the next. Putting that number in the Redis key means each
    # window gets its own fresh counter automatically.
    window_number = now // RATE_LIMIT_WINDOW_SECONDS
    redis_key = f"ratelimit:{identifier}:{window_number}"

    try:
        # A pipeline sends both commands to Redis together as one
        # all-or-nothing unit, so the counter can never end up
        # existing without an expiry time.
        pipe = redis_client.pipeline()
        pipe.incr(redis_key)  # atomic: add 1 and return the new total
        pipe.expire(redis_key, RATE_LIMIT_WINDOW_SECONDS)  # tidy up old windows
        request_count, _ = pipe.execute()
    except redis.RedisError:
        # Design decision: if Redis is unreachable, let the request
        # through ("fail open") rather than rejecting everyone
        # ("fail closed"). Availability wins over strict limiting
        # here. We log it, so an outage is visible rather than silent.
        logger.warning("Rate limiter unavailable, allowing request", exc_info=True)
        return

    if request_count > RATE_LIMIT_REQUESTS:
        seconds_left = RATE_LIMIT_WINDOW_SECONDS - (now % RATE_LIMIT_WINDOW_SECONDS)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(seconds_left)},
        )