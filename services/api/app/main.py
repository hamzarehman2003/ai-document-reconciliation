"""FastAPI application entry point. Routes are defined in app/routes/."""

from fastapi import FastAPI

from app.routes import health

app = FastAPI(title="InvoiceIQ API", version="0.1.0")

app.include_router(health.router)
