"""
Tests for per-key rate limiting. These need both Postgres and Redis
from docker-compose running.

Known quirk of a fixed window: if a test happens to straddle the
moment one window ends and the next begins, the counter resets
mid-test and the test can fail. It's rare (the requests take
milliseconds, the window is 60 seconds), so if one of these fails
once, just re-run it. That quirk is the weakness token buckets fix.
"""

from app.config import RATE_LIMIT_REQUESTS
from tests.helpers import auth, client, make_key, make_tenant


def use_up_the_limit(api_key: str) -> None:
    for _ in range(RATE_LIMIT_REQUESTS):
        response = client.get("/protected/ping", headers=auth(api_key))
        assert response.status_code == 200


def test_requests_over_the_limit_get_429():
    key = make_key(make_tenant("a"), [])
    use_up_the_limit(key)

    response = client.get("/protected/ping", headers=auth(key))

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


def test_limit_is_per_key_not_shared():
    tenant = make_tenant("a")
    busy_key = make_key(tenant, [])
    quiet_key = make_key(tenant, [])
    use_up_the_limit(busy_key)

    assert client.get("/protected/ping", headers=auth(busy_key)).status_code == 429
    # Same tenant, different key: unaffected.
    assert client.get("/protected/ping", headers=auth(quiet_key)).status_code == 200


def test_invalid_keys_are_rejected_before_rate_limiting():
    # A bad key is a 401, however many times it is tried: it never
    # reaches the rate limiter, because there is no genuine key to
    # count the requests against.
    for _ in range(RATE_LIMIT_REQUESTS + 5):
        response = client.get("/protected/ping", headers=auth("sk_live_nope.nope"))
        assert response.status_code == 401