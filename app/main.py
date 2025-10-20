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
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:8000", 
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:8000",
        "https://www.irshadsucks.com",
        "https://irshadsucks.com",
        "*"  # Allow all origins for now
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(curves.router, prefix="/api/valuation", tags=["curves"])
app.include_router(runs.router, prefix="/api/valuation", tags=["runs"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Valuation API",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "running",
        "service": "api"
    }

@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {
        "ok": True,
        "service": "api",
        "status": "healthy",
        "cors": "enabled"
    }