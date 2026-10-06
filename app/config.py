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

# Every generated key starts with this, so the "type" of key is
# recognisable at a glance (this pattern -- sk_live_... -- is the
# same one Stripe and similar services use).
KEY_PREFIX_LABEL = "sk_live"