"""
Azure App Service startup script
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))

# Import and run the FastAPI app
try:
    from app.main import app
    print("Successfully imported app.main")
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    raise

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 9000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
