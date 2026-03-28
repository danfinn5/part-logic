---
allowed-tools: Read, Glob, Grep, Edit, Write
description: Scaffold a new data source connector following the established pattern
---

Help the user add a new connector to part-logic. Follow these steps:

1. **Ask** for the connector name and source URL if not provided in $ARGUMENTS.

2. **Read** `backend/app/ingestion/base.py` to understand `BaseConnector`.

3. **Read** an existing simple connector (e.g. `backend/app/ingestion/carpart.py`) as a reference implementation.

4. **Create** `backend/app/ingestion/<name>.py` following the pattern:
   - Class extends `BaseConnector`
   - Implements `async search(self, query, **kwargs)`
   - Returns `{"market_listings": [], "salvage_hits": [], "external_links": [], "error": None}`
   - Handles all errors gracefully — catches exceptions, returns `error` string, never raises

5. **Register** the connector in `backend/app/ingestion/__init__.py`:
   - Import the new class
   - Call `register_connector(NewConnector())`

6. **Update** the connector table in `CLAUDE.md`.

7. Remind the user to add any required API keys or config to `.env` and `backend/app/config.py`.
