"""FastAPI application for Matapan Backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A local-first financial analyst for expats",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers
# from app.api import accounts, transactions, parsers

# app.include_router(accounts.router, prefix=settings.api_prefix)
# app.include_router(transactions.router, prefix=settings.api_prefix)
# app.include_router(parsers.router, prefix=settings.api_prefix)
