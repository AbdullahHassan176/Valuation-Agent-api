"""
Main FastAPI application entry point for Azure deployment
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(
    title="Valuation Agent API",
    description="Valuation API for financial instruments",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Valuation API", "version": "1.0.0", "status": "running"}

@app.get("/healthz")
def health_check():
    return {"ok": True, "service": "api", "status": "healthy", "cors": "enabled"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
