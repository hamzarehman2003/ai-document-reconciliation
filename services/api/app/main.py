"""FastAPI application entry point. Routes are defined in app/routes/."""

from fastapi import FastAPI

from app.routes import batches, documents, health, jobs, match_cases

app = FastAPI(title="InvoiceIQ API", version="0.1.0")

app.include_router(health.router)
app.include_router(batches.router)
app.include_router(documents.router)
app.include_router(jobs.router)
app.include_router(match_cases.router)
