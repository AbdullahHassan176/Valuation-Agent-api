from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Valuation Agent API",
    description="Deterministic valuation API for financial instruments",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Valuation API", "version": "1.0.0"}

@app.get("/healthz")
def health_check():
    return {"ok": True, "service": "api", "status": "healthy"}

# Try to import and include routers
try:
    from app.routers import runs, curves
    app.include_router(runs.router, prefix="/api/valuation", tags=["runs"])
    app.include_router(curves.router, tags=["curves"])
    print("Successfully loaded all routers")
except ImportError as e:
    print(f"Warning: Could not import routers: {e}")
    # Create basic endpoints
    @app.get("/api/valuation/runs")
    async def get_runs():
        return []
    
    @app.post("/api/valuation/runs")
    async def create_run():
        return {"message": "Backend not fully loaded", "status": "error"}
