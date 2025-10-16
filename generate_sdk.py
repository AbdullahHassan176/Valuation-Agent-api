#!/usr/bin/env python3
"""
Generate SDKs for frontend and backend from OpenAPI specification
"""
import json
import subprocess
import sys
from pathlib import Path

def generate_openapi_spec():
    """Generate OpenAPI specification from FastAPI app"""
    print("Generating OpenAPI specification...")
    
    # Import the app and generate OpenAPI spec
    from app import app
    openapi_spec = app.openapi()
    
    # Write to file
    with open("openapi.json", "w") as f:
        json.dump(openapi_spec, f, indent=2)
    
    print("Generated openapi.json")
    return openapi_spec

def generate_typescript_client():
    """Generate TypeScript client for frontend"""
    print("Generating TypeScript client for frontend...")
    
    frontend_sdk_path = Path("../frontend/src/sdk")
    frontend_sdk_path.mkdir(parents=True, exist_ok=True)
    
    # Use openapi-typescript-codegen
    cmd = [
        "npx", "openapi-typescript-codegen",
        "--input", "openapi.json",
        "--output", str(frontend_sdk_path),
        "--client", "axios"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Generated TypeScript client in {frontend_sdk_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating TypeScript client: {e}")
        return False
    
    return True

def generate_python_client():
    """Generate Python client for backend"""
    print("Generating Python client for backend...")
    
    backend_sdk_path = Path("../backend/sdk")
    backend_sdk_path.mkdir(parents=True, exist_ok=True)
    
    # Use openapi-python-client
    cmd = [
        "openapi-python-client", "generate",
        "--path", "openapi.json",
        "--meta", "none",
        "--output", str(backend_sdk_path)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Generated Python client in {backend_sdk_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating Python client: {e}")
        return False
    
    return True

def main():
    """Main function to generate all SDKs"""
    print("Starting SDK generation...")
    
    # Generate OpenAPI spec
    generate_openapi_spec()
    
    # Generate TypeScript client
    if not generate_typescript_client():
        print("Failed to generate TypeScript client")
        sys.exit(1)
    
    # Generate Python client
    if not generate_python_client():
        print("Failed to generate Python client")
        sys.exit(1)
    
    print("SDK generation completed successfully!")

if __name__ == "__main__":
    main()
