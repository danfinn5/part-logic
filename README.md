# PartLogic - Multi-Source Parts Search

Phase 1 implementation of PartLogic: a unified parts search backend with minimal web UI.

## Overview

PartLogic aggregates parts search results from multiple sources:
- **eBay** - Official API integration
- **RockAuto** - Web scraping (minimal implementation)
- **Row52** - Salvage yard inventory scraping (minimal implementation)
- **Car-Part.com** - Link generator only (no scraping per requirements)
- **Partsouq** - Placeholder connector (Phase 2)

## Architecture

```
backend/
  app/
    main.py              # FastAPI application entry point
    config.py            # Configuration management
    api/routes/          # API endpoints
    ingestion/           # Source connectors (isolated)
    schemas/             # Pydantic models
    utils/               # Utilities (part number extraction, normalization)

frontend/
  app/                   # Next.js app directory
    page.tsx             # Main search UI
```

## Setup

### Prerequisites

- Python 3.12 or 3.13 (3.14 not yet supported by pydantic-core)
- Node.js 18+ (for frontend)
- Redis (for caching)

**Note:** If you only have Python 3.14, install Python 3.12:
```bash
sudo dnf install python3.12 python3.12-pip  # Fedora
# Then use: python3.12 -m venv venv
```

### Backend Setup

**Quick Setup (Recommended):**
```bash
cd backend
bash setup_venv.sh
```

**Manual Setup:**
1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python3.12 -m venv venv  # Use python3.12 if you have it, or python3.13
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your eBay API keys
   ```

5. **Start Redis:**
   
   **Using Podman (Fedora default, recommended):**
   ```bash
   podman run -d -p 6379:6379 --name partlogic-redis docker.io/redis:7-alpine
   ```
   
   **Using Docker:**
   ```bash
   docker run -d -p 6379:6379 --name partlogic-redis redis:7-alpine
   ```
   
   **Or use a local Redis installation:**
   ```bash
   redis-server
   ```
   
   **Note:** If using Podman and you get "short-name resolution" errors, configure it:
   ```bash
   mkdir -p ~/.config/containers
   echo 'unqualified-search-registries = ["docker.io"]' > ~/.config/containers/registries.conf
   ```

6. **Run the backend:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   The API will be available at `http://localhost:8000`
   - API docs: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/health`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

## Environment Variables

### Required

- `EBAY_APP_ID` - eBay API Application ID (get from https://developer.ebay.com/)

### Optional

- `EBAY_CERT_ID` - eBay API Certificate ID
- `EBAY_DEV_ID` - eBay API Developer ID
- `EBAY_SANDBOX` - Use eBay sandbox (default: `true`)
- `REDIS_HOST` - Redis host (default: `localhost`)
- `REDIS_PORT` - Redis port (default: `6379`)
- `REDIS_PASSWORD` - Redis password (if required)
- `CARPART_DEFAULT_ZIP` - Default zip code for Car-Part.com searches
- `RATE_LIMIT_DELAY` - Delay between scraping requests in seconds (default: `1.0`)
- `MAX_RESULTS_PER_SOURCE` - Max results per source (default: `20`)

## API Usage

### Search Endpoint

```
GET /search?query=<search_term>&zip_code=<zip>&max_results=<number>
```

**Example:**
```bash
curl "http://localhost:8000/search?query=Honda%20Civic%20brake%20pad"
```

**Response:**
```json
{
  "query": "HONDA CIVIC BRAKE PAD",
  "extracted_part_numbers": ["CIVIC"],
  "results": {
    "market_listings": [...],
    "salvage_hits": [...],
    "external_links": [...]
  },
  "sources_queried": [
    {"source": "ebay", "status": "ok", "result_count": 15},
    {"source": "rockauto", "status": "ok", "result_count": 8},
    ...
  ],
  "warnings": [],
  "cached": false
}
```

## Caching

Results are cached in Redis for 6 hours per (source, query) combination. Cache keys:
- `{source}:{normalized_query}` - Source-specific cache
- `search:overall:{normalized_query}` - Overall result cache

Cache status is indicated in the `sources_queried` array with `status: "cached"`.

## Known Limitations (Phase 1)

1. **RockAuto Scraping**: Minimal implementation. May need adjustment based on actual site structure. If parsing fails, returns empty results with a warning.

2. **Row52 Scraping**: Best-effort implementation. HTML structure parsing may need refinement.

3. **eBay API**: Uses Finding API as fallback if Browse API fails. For production, implement OAuth 2.0 for Browse API.

4. **Partsouq**: Placeholder only - not implemented in Phase 1.

5. **Rate Limiting**: Basic rate limiting implemented. Consider more sophisticated throttling for production.

6. **Error Handling**: Sources fail gracefully, but error messages may be generic in some cases.

## Phase 2 TODOs

- [ ] Implement Partsouq connector
- [ ] Improve RockAuto scraping reliability
- [ ] Enhance Row52 parsing accuracy
- [ ] Add OAuth 2.0 for eBay Browse API
- [ ] Implement more sophisticated rate limiting
- [ ] Add result ranking/scoring
- [ ] Add pagination support
- [ ] Add filtering options (price range, condition, etc.)
- [ ] Improve part number extraction accuracy
- [ ] Add unit tests
- [ ] Add integration tests

## Development Notes

- All connectors are isolated in `app/ingestion/` for easy maintenance
- Part number extraction uses regex + heuristics (see `app/utils/part_numbers.py`)
- Normalization utilities handle price, condition, and URL formatting
- CORS is enabled for all origins in development (restrict in production)

## License

MIT
