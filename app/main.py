"""FastAPI application for deterministic valuation engine."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.settings import get_settings
from app.routers import health, curves, runs

# Create FastAPI app
app = FastAPI(
    title="Valuation API",
    description="Deterministic valuation engine for financial instruments",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Get settings
settings = get_settings()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(curves.router, tags=["curves"])
app.include_router(runs.router, prefix="/api/valuation", tags=["runs"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Valuation API",
        "version": "0.1.0",
        "docs": "/docs"
    }