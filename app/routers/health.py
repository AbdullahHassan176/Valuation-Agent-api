"""Health check endpoints."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/healthz")
async def health_check():
    """Health check endpoint.
    
    Returns:
        Health status with service information
    """
    return {
        "ok": True,
        "service": "valuation-api",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy"
    }


@router.get("/health")
async def detailed_health():
    """Detailed health check endpoint.
    
    Returns:
        Detailed health information
    """
    return {
        "ok": True,
        "service": "valuation-api",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "components": {
            "api": "healthy",
            "database": "not_configured",
            "external_services": "not_configured"
        }
    }



