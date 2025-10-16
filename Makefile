.PHONY: sdk install-deps

# Generate SDKs for frontend and backend
sdk: install-deps
	@echo "Generating OpenAPI specification..."
	@python -c "import uvicorn; from app import app; import json; import sys; print(json.dumps(app.openapi(), indent=2))" > openapi.json
	@echo "Generated openapi.json"
	
	@echo "Generating TypeScript client for frontend..."
	@npx openapi-typescript-codegen --input openapi.json --output ../frontend/src/sdk --client axios
	@echo "Generated TypeScript client in ../frontend/src/sdk"
	
	@echo "Generating Python client for backend..."
	@openapi-python-client generate --path openapi.json --meta none --output ../backend/sdk
	@echo "Generated Python client in ../backend/sdk"

# Install dependencies for SDK generation
install-deps:
	@echo "Installing SDK generation dependencies..."
	@pip install openapi-python-client
	@echo "Installed openapi-python-client"
