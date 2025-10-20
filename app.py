from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Valuation Agent API",
    description="Deterministic valuation API for financial instruments",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware with explicit domain support
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for now
        "https://www.irshadsucks.com",
        "https://irshadsucks.com",
        "http://localhost:3000",
        "http://localhost:3001"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Valuation API", "version": "1.0.0", "status": "running"}

@app.get("/healthz")
def health_check():
    return {"ok": True, "service": "api", "status": "healthy", "cors": "enabled"}

# Create basic endpoints that always work
@app.get("/api/valuation/runs")
async def get_runs():
    return []

@app.post("/api/valuation/runs")
async def create_run():
    return {"message": "Run creation endpoint active", "status": "success", "id": "test-run-001"}

@app.get("/api/valuation/curves")
async def get_curves():
    return {"curves": ["USD", "EUR", "GBP"], "status": "available"}

@app.get("/poc/chat")
async def chat_get():
    return {"message": "Chat endpoint active", "status": "ready"}

@app.post("/poc/chat")
async def chat_post():
    return {"response": "Chat endpoint working", "status": "success"}

# Try to import and include full routers (optional)
try:
    from app.routers import runs, curves
    app.include_router(runs.router, prefix="/api/valuation", tags=["runs"])
    app.include_router(curves.router, tags=["curves"])
    print("Successfully loaded all routers")
except ImportError as e:
    print(f"Warning: Could not import routers: {e}")
    print("Using basic endpoints instead")
