from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.database import get_db
from app.models import ApiKey, Tenant
from app.security import generate_api_key
from app.dependencies import get_current_key, require_scope

router = APIRouter()

class KeyListItem(BaseModel):
    id: UUID
    key_prefix: str
    scopes: list[str]
    created_at: datetime
    revoked_at: datetime | None

    class Config:
        from_attributes = True

class CreateKeyRequest(BaseModel):
    tenant_id: UUID
    scopes: list[str] = []


class CreateKeyResponse(BaseModel):
    api_key: str  # the ONLY time the real key is ever returned
    key_prefix: str


@router.post("/keys", response_model=CreateKeyResponse)
def create_key(request: CreateKeyRequest, db: Session = Depends(get_db)):
    """
    Issues a new API key for a tenant. The real key is returned
    exactly once, in this response -- it is never stored, and
    there is no way to retrieve it again later. If it's lost, the
    only option is to revoke it and issue a new one.
    """
    tenant = db.query(Tenant).filter(Tenant.id == request.tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    full_key, key_prefix, key_hash = generate_api_key()

    new_key = ApiKey(
        tenant_id=request.tenant_id,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=request.scopes,
    )
    db.add(new_key)
    db.commit()

    return CreateKeyResponse(api_key=full_key, key_prefix=key_prefix)

@router.get("/keys", response_model=list[KeyListItem])
def list_keys(
    current_key: ApiKey = Depends(require_scope("keys:read")),
    db: Session = Depends(get_db),
):
    """
    Lists keys belonging to the SAME tenant as the key making
    this request -- never another tenant's. The tenant_id filter
    below, taken from current_key rather than from anything the
    caller supplies, is what makes isolation real rather than
    optional: there's no parameter a caller could pass to see
    someone else's keys, because the filter never looks at
    caller-supplied input for this at all.
    """
    return (
        db.query(ApiKey)
        .filter(ApiKey.tenant_id == current_key.tenant_id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
 
 
@router.delete("/keys/{key_id}", status_code=204)
def revoke_key(
    key_id: UUID,
    current_key: ApiKey = Depends(require_scope("keys:write")),
    db: Session = Depends(get_db),
):
    """
    Revokes a key by setting revoked_at. Deliberately only ever
    looks up a key that ALSO belongs to current_key's tenant --
    if key_id belongs to a different tenant, this returns 404,
    exactly as if the key didn't exist at all. Returning 403
    ("exists, but not yours") instead would confirm to a caller
    that a given key_id is real, which leaks information about
    another tenant's data.
    """
    key_to_revoke = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.tenant_id == current_key.tenant_id)
        .first()
    )
 
    if key_to_revoke is None:
        raise HTTPException(status_code=404, detail="Key not found")
 
    key_to_revoke.revoked_at = func.now()
    db.commit()

@router.get("/protected/ping")
def protected_ping(current_key: ApiKey = Depends(get_current_key)):
    """
    A placeholder protected endpoint, only reachable with a valid,
    non-revoked key. This exists purely to prove the
    authentication flow works end to end -- week 3 will build
    real functionality (and scope checks) behind endpoints like
    this one.
    """
    return {
        "message": "Authenticated successfully",
        "tenant_id": str(current_key.tenant_id),
        "key_prefix": current_key.key_prefix,
    }