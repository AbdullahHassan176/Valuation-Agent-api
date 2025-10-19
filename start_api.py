#!/usr/bin/env python3
"""
Simple API server startup script
"""
import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print(f"Current directory: {current_dir}")
print(f"Python path: {sys.path[:3]}...")

try:
    from app.main import app
    print("✅ App imported successfully")
    
    import uvicorn
    print("✅ Uvicorn imported successfully")
    
    print("🚀 Starting API server on http://127.0.0.1:9000")
    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="info")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

