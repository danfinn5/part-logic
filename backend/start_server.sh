#!/bin/bash
# Start PartLogic backend server
# Uses absolute path to Python 3.12 to avoid shell interception issues

cd "$(dirname "$0")"

# Add venv site-packages to Python path
VENV_SITE_PACKAGES="$(pwd)/venv/lib/python3.12/site-packages"
export PYTHONPATH="$VENV_SITE_PACKAGES:$PYTHONPATH"

# Start server using absolute Python path
exec /usr/bin/python3.12 -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
