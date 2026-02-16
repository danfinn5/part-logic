# CLAUDE.md — part-logic

Auto parts search aggregator: FastAPI backend + Next.js frontend. Searches multiple parts sources in parallel and returns unified results.

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

**API endpoints:** `GET /search?query=...&zip_code=...&max_results=...&sort=value|relevance|price_asc|price_desc`, `GET /docs`, `GET /health`

## Architecture

### Connector Pattern

All data sources implement `BaseConnector` (in `app/ingestion/base.py`) with an `async search()` method returning `{market_listings, salvage_hits, external_links, error}`.

**Active connectors** (`app/ingestion/`):
| Connector | Source | Type |
|-----------|--------|------|
| `ebay.py` | eBay | Official API |
| `rockauto.py` | RockAuto | Web scraper |
| `row52.py` | Row52 | Salvage yard scraper |
| `carpart.py` | Car-Part.com | Link generator |
| `partsouq.py` | Partsouq | Web scraper |
| `ecstuning.py` | ECS Tuning | Web scraper |
| `fcpeuro.py` | FCP Euro | Web scraper |
| `amazon.py` | Amazon | Web scraper |
| `partsgeek.py` | PartsGeek | Web scraper |
| `resources.py` | Resource links | Static links |

Connectors self-register via `register_connector()` in `app/ingestion/__init__.py`.

### Key modules
- `app/api/routes/search.py` — Main search endpoint; fans out to connectors, caches in Redis (6h TTL)
- `app/schemas/` — Pydantic v2 models: `MarketListing`, `SalvageHit`, `ExternalLink`, `ListingGroup`, `Offer`, `SearchResponse`
- `app/utils/part_numbers.py` — Part number extraction/normalization from free-text queries
- `app/utils/grouping.py` — Groups listings by (brand, part_number) for price comparison across retailers; computes value scores (quality/price ratio)
- `app/utils/ranking.py` — Multi-factor relevance scoring + value sort (quality-per-dollar)
- `app/utils/brand_intelligence.py` — Brand comparison using 50+ brand profiles
- `app/utils/query_analysis.py` — Query classification (part_number, vehicle_part, keywords)
- `app/utils/interchange.py` — Multi-provider cross-reference expansion
- `app/config.py` — Pydantic Settings from `.env`

### Data flow
`search route → query analysis → interchange expansion → smart connector routing → parallel fan-out → deduplicate → rank → group by brand+part for comparison → build brand comparison → cache → SearchResponse`

## Requirements

- Python 3.12+ (3.13 works, 3.14 NOT supported due to pydantic-core)
- Redis for caching (optional — degrades gracefully)
- eBay API keys in `.env` for eBay source
- Node.js for frontend

## Adding a New Connector

1. Create `app/ingestion/newsite.py` with a class extending `BaseConnector`
2. Implement `async search(self, query, **kwargs)` returning the standard dict format
3. Register it in `app/ingestion/__init__.py`: import + `register_connector(NewSiteConnector())`
4. Handle errors gracefully — return `error` string, never raise
