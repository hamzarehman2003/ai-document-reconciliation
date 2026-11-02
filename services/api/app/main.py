"""FastAPI application entry point. Routes are defined in app/routes/."""

from fastapi import Depends, FastAPI

from app.auth import get_current_user
from app.routes import (
    audit,
    batches,
    dashboard,
    documents,
    exports,
    health,
    jobs,
    match_cases,
    webhooks,
)

app = FastAPI(title="InvoiceIQ API", version="0.1.0")

# Health stays public (the status dot). Webhooks check their own API key.
# Everything else needs a signed-in user.
app.include_router(health.router)
app.include_router(webhooks.router)
for module in (batches, documents, jobs, match_cases, audit, exports, dashboard):
    app.include_router(module.router, dependencies=[Depends(get_current_user)])
