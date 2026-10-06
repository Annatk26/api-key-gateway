from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tenant

router = APIRouter()


class CreateTenantRequest(BaseModel):
    name: str


class TenantResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    class Config:
        # Lets Pydantic read values directly off the SQLAlchemy
        # Tenant object's attributes, rather than requiring a
        # plain dict -- without this, returning `tenant` directly
        # from the endpoint below would fail.
        from_attributes = True


@router.post("/tenants", response_model=TenantResponse)
def create_tenant(request: CreateTenantRequest, db: Session = Depends(get_db)):
    """
    Creates a new tenant. This is deliberately open with no
    authentication for now, since a tenant doesn't have any API
    keys yet at the point they're being created -- there's
    nothing to authenticate against.

    Worth flagging as a known simplification: a real version of
    this service would put some gate in front of this endpoint
    (e.g. an admin key, or a proper sign-up flow with email
    verification) so anyone can't freely create tenants. Left
    open here since only you are using this locally.
    """
    tenant = Tenant(name=request.name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)  # loads the DB-generated id and created_at back onto the object
    return tenant