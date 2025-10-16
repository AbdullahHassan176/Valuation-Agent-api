# Valuation-Agent-api

Deterministic valuation API for Valuation Agent Workspace.

## How to run (Phase 0)

### Local Development
```bash
# Install dependencies
pip install fastapi uvicorn[standard] pydantic

# Run the server
uvicorn app:app --host 0.0.0.0 --port 9000
```

### Generate SDKs
```bash
# Install SDK generation dependencies
pip install openapi-python-client

# Generate SDKs for frontend and backend
python generate_sdk.py
# OR use Makefile (if make is available)
make sdk
```

### Testing
```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=. --cov-report=html
```

### Docker
```bash
# From parent directory
docker compose up --build
```

### Health Check
- GET http://localhost:9000/healthz → `{"ok": true, "service": "api"}`

### OpenAPI Documentation
- GET http://localhost:9000/docs → Interactive API documentation
- GET http://localhost:9000/redoc → ReDoc API documentation
- GET http://localhost:9000/openapi.json → OpenAPI specification

### Available Endpoints
- POST /runs - Create a new valuation run (with validation and queuing)
- GET /runs/{id} - Get run status
- GET /runs/{id}/result - Get run result (calculated with dummy pricing)

### Features
- **Validation**: Comprehensive validation of IRS/CCS specifications
- **Queuing**: Asynchronous processing of valuation runs
- **Pricing**: Dummy pricing functions for IRS and CCS (ready for QuantLib integration)
- **Curves**: Curve bootstrapping and interpolation (placeholder implementation)
- **Lineage**: Full lineage tracking with market data and model hashes
