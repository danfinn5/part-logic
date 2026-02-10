"""
Shared fixtures for PartLogic backend tests.
"""
import pytest
import sys
import os

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force env vars so Settings doesn't fail on missing .env
os.environ.setdefault("EBAY_APP_ID", "")
os.environ.setdefault("EBAY_CERT_ID", "")
os.environ.setdefault("EBAY_SANDBOX", "true")


@pytest.fixture
def sample_ebay_item():
    """Sample eBay Browse API item summary."""
    return {
        "itemId": "v1|123456|0",
        "title": "Bosch Brake Pad Set BP1234 Front Ceramic",
        "price": {"value": "42.99", "currency": "USD"},
        "condition": "New",
        "itemWebUrl": "https://www.ebay.com/itm/123456",
        "buyingOptions": ["FIXED_PRICE"],
        "shippingOptions": [
            {"shippingCost": {"value": "5.99", "currency": "USD"}}
        ],
        "seller": {"username": "autoparts_seller"},
        "image": {"imageUrl": "https://i.ebayimg.com/images/g/abc/s-l225.jpg"},
    }


@pytest.fixture
def sample_ebay_item_auction():
    """Sample eBay Browse API auction item."""
    return {
        "itemId": "v1|789012|0",
        "title": "OEM Honda 12345-ABC Timing Belt Kit",
        "price": {"value": "18.50", "currency": "USD"},
        "condition": "Used",
        "itemWebUrl": "https://www.ebay.com/itm/789012",
        "buyingOptions": ["AUCTION"],
        "seller": {"username": "junkyard_joe"},
        "image": {"imageUrl": "https://i.ebayimg.com/images/g/xyz/s-l225.jpg"},
    }
