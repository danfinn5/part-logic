# Ingestion Connectors — Agent Guide

This directory contains all data source connectors for the parts search aggregator.

## How to Add a New Connector

1. **Create a new file** in this directory: `newsite.py`
2. **Subclass `BaseConnector`** from `base.py`
3. **Implement `async search(self, query: str, **kwargs) -> Dict[str, Any]`**
   - Must return: `{"market_listings": [...], "salvage_hits": [...], "external_links": [...], "error": None}`
   - Use `MarketListing`, `SalvageHit`, `ExternalLink` from `app.schemas`
4. **Register** in `__init__.py`: add import + `register_connector(NewSiteConnector())`
5. **Handle errors gracefully**: catch exceptions, return `error` string, never crash

## Connector Types

- **API connectors** (e.g., `ebay.py`): Use official API with auth tokens from config
- **Web scrapers** (e.g., `rockauto.py`, `amazon.py`): Use `httpx` + `beautifulsoup4`, handle rate limits
- **Link generators** (e.g., `carpart.py`): Build URLs without fetching, return as `external_links`
- **Static** (e.g., `resources.py`): Return fixed resource links

## Important Patterns

- Always use `httpx.AsyncClient` for HTTP requests (not `requests`)
- Set timeouts (10-30s) on all HTTP calls
- Source name in `__init__` should be lowercase, no spaces (used as cache key prefix)
- Test with: `python -m pytest tests/` from `backend/`
