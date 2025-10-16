from fastapi import FastAPI
from app.routers import runs, curves

app = FastAPI(
    title="Valuation Agent API",
    description="Deterministic valuation API for financial instruments",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers
app.include_router(runs.router)
app.include_router(curves.router)

@app.get("/healthz")
def health_check():
    return {"ok": True, "service": "api"}
