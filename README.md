# Valuation API

Deterministic valuation engine for financial instruments.

## Features

- FastAPI-based REST API
- Support for various financial instruments
- QuantLib integration for pricing models
- Comprehensive Pydantic schemas
- Health check endpoints
- CORS support for frontend integration

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry

### Installation

```bash
# Install dependencies
poetry install

# Run the development server
poetry run uvicorn app.main:app --reload
```

### API Endpoints

- `GET /` - Root endpoint
- `GET /healthz` - Health check
- `GET /health` - Detailed health check
- `GET /docs` - API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation

### Testing

```bash
# Test health endpoint
curl http://localhost:9000/healthz

# Expected response:
# {"ok":true,"service":"valuation-api","timestamp":"2024-01-01T00:00:00","status":"healthy"}
```

## Development

### Project Structure

```
api/
├── app/
│   ├── main.py              # FastAPI application
│   ├── settings.py          # Configuration
│   ├── routers/
│   │   └── health.py        # Health endpoints
│   └── core/
│       └── models.py        # Pydantic schemas
├── pyproject.toml           # Poetry dependencies
├── Dockerfile              # Container configuration
└── README.md               # This file
```

### Adding New Endpoints

1. Create a new router in `app/routers/`
2. Import and include the router in `app/main.py`
3. Add corresponding Pydantic models in `app/core/models.py`

### Environment Variables

- `PORT` - Server port (default: 9000)
- `HOST` - Server host (default: 0.0.0.0)
- `DEBUG` - Debug mode (default: False)

## Docker

```bash
# Build image
docker build -t valuation-api .

# Run container
docker run -p 9000:9000 valuation-api
```

## License

MIT