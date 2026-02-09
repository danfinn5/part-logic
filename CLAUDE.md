# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Overview

This is a multi-project workspace containing three independent projects:

- **part-logic/** — Full-stack parts search aggregator (FastAPI backend + Next.js frontend)
- **danfinn5.github.io/** — Hugo/Docsy technical writing portfolio, deployed to Netlify
- **thinkpad tuning/** — Shell scripts for ThinkPad T480s system optimization

## part-logic

### Build & Run Commands

**Backend** (from `part-logic/backend/`):
```bash
# Setup virtual environment
bash setup_venv.sh                    # Creates venv with Python 3.12
source venv/bin/activate
pip install -r requirements.txt

# Run development server
bash start_server.sh                  # Or directly:
python3.12 -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

# API endpoints
# GET /search?query=...&zip_code=...&max_results=...
# GET /docs       (interactive Swagger docs)
# GET /health
```

**Frontend** (from `part-logic/frontend/`):
```bash
npm install
npm run dev       # Development server
npm run build     # Production build
npm run lint      # ESLint via Next.js
```

### Architecture

The backend uses a **connector pattern** for aggregating results from multiple auto parts sources into a unified response format:

- `app/ingestion/base.py` — Abstract `BaseConnector` class defining the `search()` interface. All connectors return a dict with `market_listings`, `salvage_hits`, `external_links`, and optional `error`.
- `app/ingestion/ebay.py` — eBay official API connector
- `app/ingestion/rockauto.py` — RockAuto web scraper
- `app/ingestion/row52.py` — Row52 salvage yard scraper
- `app/ingestion/carpart.py` — Car-Part.com link generator (no scraping)
- `app/ingestion/partsouq.py` — Placeholder for Phase 2

Key data flow: `search route → fan-out to connectors → normalize results → cache in Redis → unified SearchResponse`

- `app/api/routes/search.py` — Main search endpoint; orchestrates connectors, handles Redis caching (6-hour TTL)
- `app/schemas/` — Pydantic models (`MarketListing`, `SalvageHit`, `ExternalLink`, `SearchResponse`)
- `app/utils/part_numbers.py` — Part number extraction/normalization from free-text queries
- `app/config.py` — Pydantic Settings loading from `.env` file

The frontend is a minimal Next.js 14 App Router setup with a single search page (`app/page.tsx`) that calls the backend API.

**Requirements:** Python 3.12+ (3.13 works, 3.14 unsupported due to pydantic-core), Redis for caching (optional — degrades gracefully), eBay API keys in `.env` for eBay source.

## danfinn5.github.io

### Build & Run Commands

From `danfinn5.github.io/`:
```bash
npm install
npm run serve              # Local dev server with live reload
npm run build              # Dev build
npm run build:production   # Production build (minified + encrypted samples)
npm run build:preview      # Preview build (includes drafts)
npm run test               # Link checking
npm run clean              # Remove generated files
```

### Architecture

Hugo static site using the Docsy theme (Google's technical docs theme) with submodules. Content is in `content/en/` with multilingual support (en/fa/no). Custom layouts in `layouts/`, SCSS in `assets/scss/`. Deployed to Netlify via `netlify.toml` with GitHub Actions CI. Sample content behind basic-auth uses an encryption script (`encrypt-samples.sh`).

**Requires:** Hugo Extended 0.110.0+, Node.js LTS, Go (for Hugo modules).

## thinkpad tuning

Shell scripts — no build system. `tune-thinkpad.sh` is the main script. See `THINKPAD_TUNING.md` for documentation. Scripts must be run with appropriate privileges (sudo).
