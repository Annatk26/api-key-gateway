"""
Loads configuration from the .env file at the project root.

We reuse the same Postgres credentials docker-compose.yml uses,
rather than duplicating the password in a second place. .env is
the single source of truth for secrets.
"""

import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_DB = os.environ["POSTGRES_DB"]

# The app runs on your machine, outside Docker, so it connects to
# Postgres via "localhost" on the port docker-compose.yml exposed
# (5432) -- not the internal container network.
DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@localhost:5432/{POSTGRES_DB}"
)

# Redis is reached the same way: localhost, on the port
# docker-compose.yml exposed (6379). Database 0 is Redis's default.
REDIS_URL = "redis://localhost:6379/0"

# Every generated key starts with this, so the "type" of key is
# recognisable at a glance (this pattern -- sk_live_... -- is the
# same one Stripe and similar services use).
KEY_PREFIX_LABEL = "sk_live"

# Rate limiting: each key may make RATE_LIMIT_REQUESTS requests per
# RATE_LIMIT_WINDOW_SECONDS. The defaults are deliberately low so
# the limit is easy to hit while testing. Override them by setting
# environment variables of the same name.
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))