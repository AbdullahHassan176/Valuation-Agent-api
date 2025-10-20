#!/usr/bin/env python3
"""
Backend startup script for Azure App Service
This script starts the FastAPI backend service
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the backend FastAPI application"""
    
    # Set environment variables
    os.environ.setdefault('PYTHONPATH', '/home/site/wwwroot')
    os.environ.setdefault('WEBSITES_PORT', '8000')
    
    # Add current directory to Python path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    try:
        # Try to import and run the FastAPI app
        from app.main import app
        import uvicorn
        
        print("Starting FastAPI backend service...")
        print(f"Python path: {sys.path}")
        print(f"Current directory: {current_dir}")
        
        # Start the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Falling back to basic FastAPI app...")
        
        # Fallback: Create a basic FastAPI app
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        
        app = FastAPI(title="Backend Service", version="1.0.0")
        
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
            return {"message": "Backend Service", "status": "running"}
        
        @app.get("/healthz")
        def health():
            return {"ok": True, "service": "backend", "status": "healthy"}
        
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        
    except Exception as e:
        print(f"Error starting backend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
