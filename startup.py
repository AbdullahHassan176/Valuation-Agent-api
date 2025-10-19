"""
Azure Static Web Apps startup script for the API.
This file is used to configure the FastAPI app for Azure deployment.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set environment variables for Azure
os.environ.setdefault("PORT", "80")
os.environ.setdefault("HOST", "0.0.0.0")

# Import and configure the FastAPI app
from app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 80))
    uvicorn.run(app, host="0.0.0.0", port=port)
