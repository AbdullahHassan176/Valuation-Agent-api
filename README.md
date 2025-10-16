# Valuation-Agent-api

Deterministic valuation API for Valuation Agent Workspace.

## How to run (Phase 0)

### Local Development
```bash
# Install dependencies
pip install fastapi uvicorn[standard]

# Run the server
uvicorn app:app --host 0.0.0.0 --port 9000
```

### Docker
```bash
# From parent directory
docker compose up --build
```

### Health Check
- GET http://localhost:9000/healthz → `{"ok": true, "service": "api"}`
