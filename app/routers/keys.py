from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey, Tenant
from app.security import generate_api_key
from app.dependencies import get_current_key

router = APIRouter()


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