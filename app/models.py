"""
Python classes that mirror the tables created in db/schema.sql.

The SQL file is the source of truth for the actual table
structure -- these classes just give us a way to read and write
rows as ordinary Python objects instead of writing raw SQL by
hand for every query. If a column here doesn't match schema.sql
exactly, queries will fail at runtime, so keep the two in sync.
"""

import uuid
from sqlalchemy import Column, String, DateTime, ARRAY, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    key_prefix = Column(String, unique=True, nullable=False)
    key_hash = Column(String, nullable=False)
    scopes = Column(ARRAY(String), nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)