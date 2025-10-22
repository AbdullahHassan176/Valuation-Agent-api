"""
Simple Azure App Service startup script
This version focuses on getting the basic app running
"""
import os
import sys

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = current_dir

print(f"Starting simple backend...")
print(f"Current directory: {current_dir}")
print(f"Python path: {sys.path[:3]}")

# Import and run the FastAPI app
try:
    from app import app
    print("✅ Successfully imported app")
    
    if __name__ == "__main__":
        import uvicorn
        port = int(os.environ.get("PORT", 9000))
        print(f"🚀 Starting server on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    
    # Create a minimal FastAPI app as fallback
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    fallback_app = FastAPI(title="Valuation API Fallback")
    
    fallback_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @fallback_app.get("/")
    def root():
        return {"message": "Valuation API Fallback", "status": "running"}
    
    @fallback_app.get("/healthz")
    def health():
        return {"ok": True, "status": "fallback"}
    
    if __name__ == "__main__":
        import uvicorn
        port = int(os.environ.get("PORT", 9000))
        print(f"🚀 Starting fallback server on port {port}")
        uvicorn.run(fallback_app, host="0.0.0.0", port=port)

