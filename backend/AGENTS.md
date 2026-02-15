# Part-Logic Backend — Agent Guide

FastAPI backend for the auto parts search aggregator.

## Directory Structure

```
app/
├── api/routes/search.py  — Main search endpoint (GET /search)
├── ingestion/            — Data source connectors (see ingestion/AGENTS.md)
├── schemas/              — Pydantic v2 response models
├── utils/part_numbers.py — Part number parsing and normalization
├── config.py             — Settings from .env via Pydantic Settings
└── main.py               — FastAPI app setup, CORS, lifespan
```

## Running

```bash
source venv/bin/activate   # Python 3.12 venv
bash start_server.sh       # uvicorn on port 8000
```

## Key Decisions

- Python 3.12 only (3.14 breaks pydantic-core)
- All connectors run in parallel via asyncio
- Redis caching is optional — app works without it
- Never commit `.env` (contains API keys)
- Scrapers should degrade gracefully on failure (return error string, not exception)
