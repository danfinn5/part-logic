"""
Shared fixtures for PartLogic backend tests.
"""

import os
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force env vars so Settings doesn't fail on missing .env
os.environ.setdefault("EBAY_APP_ID", "")
os.environ.setdefault("EBAY_CERT_ID", "")
os.environ.setdefault("EBAY_SANDBOX", "true")
