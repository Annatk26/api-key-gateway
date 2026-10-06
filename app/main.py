from fastapi import FastAPI

from app.routers import keys
from app.routers import tenants

app = FastAPI(title="API Key Management Service")

app.include_router(keys.router)
app.include_router(tenants.router)


@app.get("/health")
def health():
    """Simple liveness check -- not part of the core project,
    just useful for confirming the server is up at all."""
    return {"status": "ok"}