# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Auto parts search aggregator: FastAPI backend + Next.js frontend. Searches multiple parts sources in parallel and returns unified results with AI-powered intelligence.

## Build & Run

**Backend** (from `backend/`):
```bash
bash setup_venv.sh              # Creates venv with Python 3.12
source venv/bin/activate
pip install -r requirements.txt
bash start_server.sh            # Or: python3.12 -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

**Frontend** (from `frontend/`):
```bash
npm install
npm run dev       # Dev server
npm run build     # Production build
npm run lint      # ESLint
```

**Testing** (from `backend/`):
```bash
python -m pytest tests/ -v                                  # Full suite (~296 tests)
python -m pytest tests/test_connectors.py -v                # Single file
python -m pytest tests/test_connectors.py::test_ebay_search -v  # Single test
```

**Linting** (from `backend/`):
```bash
ruff check --fix .    # Lint
ruff format .         # Format
```

**API endpoints:** `GET /search`, `GET /vin/decode`, `POST/GET/DELETE /saved/searches`, `POST/GET /saved/alerts`, `GET /history/searches`, `GET /history/prices`, `GET /sources`, `GET /canonical/*`, `GET /docs`, `GET /health`

## Architecture

### Connector Pattern

All data sources implement `BaseConnector` (`app/ingestion/base.py`) with an `async search()` method returning `{market_listings, salvage_hits, external_links, error}`. Connectors self-register via `register_connector()` in `app/ingestion/__init__.py`.

**17 connectors** (`app/ingestion/`):

| Type | Connectors |
|------|-----------|
| Official API | `ebay.py` (Browse API, OAuth 2.0) |
| HTTP scrapers | `row52.py`, `ecstuning.py`, `fcpeuro.py`, `partsouq.py`, `carpart.py` |
| Playwright scrapers | `rockauto.py`, `partsgeek.py`, `amazon.py` |
| Link generators | `autozone.py`, `oreilly.py`, `napa.py`, `lkq.py`, `advanceauto.py` |
| Static | `resources.py` (YouTube/Charm.li) |

Config toggles: `scrape_enabled` (global scraping on/off), `playwright_enabled` (Chromium-based scrapers). When disabled, scrapers fall back to link generation.

### Search Data Flow

```
query → query analysis (PART_NUMBER | VEHICLE_PART | KEYWORDS)
      → VIN decode (optional, NHTSA vPIC API, 30-day cache)
      → AI advisor (parallel, 25s timeout)
      → community fetch (parallel, Reddit, 5s timeout, 7-day cache)
      → interchange expansion (cross-reference)
      → vehicle resolution (alias → canonical vehicle_id)
      → fitment checking (canonical fitments table)
      → smart connector routing (source registry → fallback defaults)
      → parallel connector fan-out
      → deduplicate → rank → group by (brand, part_number) → brand comparison
      → Redis cache (6h TTL) + SQLite history
      → SearchResponse
```

### Services (`app/services/`)

- **`ai_advisor.py`** — AI analysis with fallback chain: Gemini (free) → OpenAI (gpt-4.1-nano) → Anthropic. Returns structured recommendations, OEM part numbers, brand suggestions. Runs in parallel with search, 25s timeout.
- **`vin_decoder.py`** — NHTSA vPIC API (free, no auth), 30-day cache.
- **`community.py`** — Reddit discussion fetcher. Make-specific + general automotive subs, 5s timeout, 7-day cache.
- **`fitment_checker.py`** — Queries canonical `fitments` table. Returns `confirmed_fit` (confidence ≥ 80) or `likely_fit`.
- **`vehicle_resolver.py`** — Maps loose year/make/model strings to canonical `vehicle_id` via `vehicle_aliases` table.
- **`price_alert_checker.py`** — Background job checking saved searches against current prices.

### Key Utilities (`app/utils/`)

- `query_analysis.py` — `QueryType` enum drives connector routing + ranking boosts
- `grouping.py` — Clusters same part across retailers by (brand, part_number) for price comparison; computes value scores
- `ranking.py` — Multi-factor relevance scoring + value sort (quality-per-dollar)
- `interchange.py` / `cross_reference.py` — Multi-provider cross-reference expansion
- `brand_intelligence.py` — Brand comparison using 50+ profiles in `app/data/brand_knowledge.py`
- `part_numbers.py` — Part number extraction/normalization from free-text queries

### Source Registry

`app/data/source_registry.py` + `app/data/sources_registry.json` — JSON-backed registry of 119+ sources with metadata (category, tags, priority, capabilities). Drives smart connector routing in `search.py`. Sources can be toggled at runtime without code changes.

### Database

- **SQLite** (`data/partlogic.db` via `app/db.py`): search history, price snapshots, saved searches, price alerts, canonical data (vehicles, aliases, configs, parts, part_numbers, fitments, supersessions, interchange groups)
- **`app/db_canonical.py`**: CRUD operations for canonical vehicle/part/fitment data
- **Redis**: Optional 6-hour cache per (source, query). Degrades gracefully if unavailable.

### Frontend

Next.js 14 App Router + TypeScript + TailwindCSS.

**Pages:** `/` (main search with VIN input, AI summary, comparison/list views, saved searches), `/prices` (price history), `/admin` (canonical data management: vehicles, aliases, fitments, parts).

**Key components** (`app/components/`): `AISummary`, `AIRecommendations`, `ComparisonView`, `ListingGrid`, `ListingCard`, `PriceChart`, `SalvageSection`, `ExternalLinksSection`, `SourceStatusBar`, `SavedSearches`, `LoadingSkeleton`.

**API client:** `app/lib/api.ts`. **Types:** `app/lib/types.ts` (mirrors backend Pydantic schemas).

### Data Import Scripts (from `backend/`)

`import_vehicles.py`, `import_aliases.py`, `import_parts.py`, `import_fitments.py`, `import_sources.py` — CSV import scripts for canonical data. Templates in `data/templates/`.

## Conventions

**Backend:**
- Use `httpx` for async HTTP requests (not `requests`). Use `beautifulsoup4` for HTML parsing.
- Pydantic v2 for all data models (`app/schemas/`). Pydantic Settings for config (`app/config.py`).
- Use async route handlers. FastAPI app uses lifespan pattern (not deprecated `on_event`).

**Frontend:**
- Keep it minimal — this is a search UI, not a complex SPA.
- Prefer server components by default; use `"use client"` only when needed (interactivity, hooks).
- API calls go to the FastAPI backend at `http://localhost:8000`.

## Testing Patterns

- pytest-asyncio strict mode: tests need `@pytest.mark.asyncio`, async fixtures need `@pytest_asyncio.fixture`
- Playwright connectors: mock `get_page` context manager
- Search route tests: mock Redis (`get_cached_result`/`set_cached_result`), `enrich_with_cross_references`, `build_interchange_group`, `get_ai_recommendations`

## Pre-commit Hooks

Ruff lint (`--fix --exit-non-zero-on-fix`) + ruff format on `backend/` files. `no-commit-to-branch` blocks direct commits to `main`.

## Requirements

- Python 3.12+ (3.13 works, 3.14 NOT supported — pydantic-core incompatibility)
- Node.js LTS for frontend
- Redis for caching (optional)
- eBay API keys in `.env` for eBay source
- Ruff config: `backend/ruff.toml` (line-length 120, double quotes)
- Config via `.env` file (copy from `.env.example`). Key vars: `EBAY_APP_ID`, `EBAY_CERT_ID`, `REDIS_HOST`/`REDIS_PORT`, `CARPART_DEFAULT_ZIP`, `RATE_LIMIT_DELAY`, `MAX_RESULTS_PER_SOURCE`

## Adding a New Connector

1. Create `app/ingestion/newsite.py` with a class extending `BaseConnector`
2. Implement `async search(self, query, **kwargs)` returning the standard dict format
3. Register it in `app/ingestion/__init__.py`: import + `register_connector(NewSiteConnector())`
4. Handle errors gracefully — return `error` string, never raise
5. Add the source to `app/data/sources_registry.json` for smart routing
