from fastapi import FastAPI
from .routers import runs, curves, exports, sensitivities, marketdata

app = FastAPI(
    title="Valuation Agent API",
    description="Deterministic valuation API for financial instruments with QuantLib integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers
app.include_router(runs.router)
app.include_router(curves.router)
app.include_router(exports.router)
app.include_router(sensitivities.router)
app.include_router(marketdata.router)

@app.get("/healthz")
def health_check():
    return {"ok": True, "service": "api"}
