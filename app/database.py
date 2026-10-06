"""
Sets up the connection to Postgres.

We're using SQLAlchemy here as a toolkit for writing Python
objects that map to our existing tables, rather than writing raw
SQL strings everywhere in the application code. Note that the
tables themselves were already created by db/schema.sql when
Postgres first started -- SQLAlchemy is not creating tables here,
only connecting to and querying ones that already exist.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL

# The engine manages the actual connection(s) to Postgres.
engine = create_engine(DATABASE_URL)

# A "session" is one conversation with the database -- created
# fresh for each request, used for a set of queries, then closed.
# Reusing one long-lived connection across many requests causes
# subtle bugs, so a fresh session per request is the standard
# pattern.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    A FastAPI dependency: creates one database session per
    request, hands it to the endpoint function, and guarantees
    it's closed afterward -- even if the endpoint raises an error.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()