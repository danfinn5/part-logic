# PartLogic Setup Guide

Auto parts search aggregator with a FastAPI backend and Next.js frontend. Searches eBay, RockAuto, Amazon, ECS Tuning, FCP Euro, PartsGeek, Row52, and more in parallel.

---

## Prerequisites

- **Python 3.12** (3.13 works; 3.14 does NOT due to pydantic-core)
- **Node.js** (v18+ recommended)
- **Redis** (optional — app degrades gracefully without it)
- Git

---

## 1. Clone the repo

```bash
git clone <repo-url>
cd part-logic
```

---

## 2. Backend setup

```bash
cd backend

# Create Python 3.12 virtual environment and install dependencies
bash setup_venv.sh

# Activate the venv
source venv/bin/activate
```

### Environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values. At minimum you'll want:

| Variable | Required | Notes |
|----------|----------|-------|
| `EBAY_APP_ID` | For eBay results | Get from [developer.ebay.com](https://developer.ebay.com/) |
| `EBAY_CERT_ID` | For eBay results | Same developer account |
| `EBAY_DEV_ID` | For eBay results | Same developer account |
| `GEMINI_API_KEY` | For AI Advisor feature | Free key at [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `REDIS_HOST` | Optional | Defaults to `localhost:6379` |

> **AI Advisor** uses the first key it finds in priority order: Gemini (free) → OpenAI → Anthropic. You only need one.

> **eBay** — set `EBAY_SANDBOX=false` in `.env` once you have production keys.

### Start the backend

```bash
bash start_server.sh
# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

---

## 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
# Dev server at http://localhost:3000
```

---

## 4. API usage

```
GET /search?query=brake+pads&zip_code=90210&max_results=20&sort=value
```

**Sort options:** `value` | `relevance` | `price_asc` | `price_desc`

Other endpoints: `GET /health`, `GET /docs`

---

## 5. Redis (optional but recommended)

Redis caches search results for 6 hours, making repeated queries instant.

```bash
# macOS
brew install redis && brew services start redis

# Ubuntu/Debian
sudo apt install redis-server && sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

---

## 6. Project structure

```
part-logic/
├── backend/
│   ├── app/
│   │   ├── api/routes/search.py   # Main search endpoint
│   │   ├── ingestion/             # Data source connectors
│   │   │   ├── base.py            # BaseConnector interface
│   │   │   ├── ebay.py            # eBay (official API)
│   │   │   ├── amazon.py          # Amazon (scraper)
│   │   │   ├── rockauto.py        # RockAuto (scraper)
│   │   │   ├── row52.py           # Row52 salvage (scraper)
│   │   │   ├── ecstuning.py       # ECS Tuning (scraper)
│   │   │   ├── fcpeuro.py         # FCP Euro (scraper)
│   │   │   ├── partsgeek.py       # PartsGeek (scraper)
│   │   │   ├── partsouq.py        # Partsouq (scraper)
│   │   │   ├── carpart.py         # Car-Part.com (link gen)
│   │   │   └── resources.py       # Static resource links
│   │   ├── schemas/               # Pydantic v2 models
│   │   ├── utils/                 # Ranking, grouping, brand intelligence
│   │   └── config.py              # Settings from .env
│   ├── requirements.txt
│   ├── setup_venv.sh
│   └── start_server.sh
└── frontend/
    ├── app/                       # Next.js app directory
    ├── package.json
    └── tailwind.config.ts
```

---

## 7. Adding a new data source connector

1. Create `backend/app/ingestion/mysource.py` extending `BaseConnector`
2. Implement `async search(self, query, **kwargs)` returning:
   ```python
   {
       "market_listings": [...],
       "salvage_hits": [...],
       "external_links": [...],
       "error": None  # or an error string — never raise
   }
   ```
3. Register it in `backend/app/ingestion/__init__.py`:
   ```python
   from .mysource import MySourceConnector
   register_connector(MySourceConnector())
   ```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `pydantic-core` build fails | Make sure you're on Python 3.12 or 3.13, not 3.14 |
| eBay returns no results | Check `EBAY_SANDBOX=false` and your API keys in `.env` |
| Redis connection errors | App still works without Redis; errors are non-fatal |
| Scraper returns empty | Some sites block scrapers; try again or check for site changes |
| `venv/bin/python` points to wrong Python | Run `bash setup_venv.sh` again — it fixes broken symlinks |
