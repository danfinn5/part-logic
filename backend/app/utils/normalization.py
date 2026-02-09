"""
Data normalization utilities for unifying results from different sources.
"""
from typing import Any, Dict, List
from app.schemas.search import MarketListing, SalvageHit, ExternalLink


def normalize_price(price_str: Any, currency: str = "USD") -> float:
    """
    Normalize price string to float.
    Handles various formats: "$123.45", "123.45", "123,45.00", etc.
    """
    if price_str is None:
        return 0.0
    
    if isinstance(price_str, (int, float)):
        return float(price_str)
    
    if isinstance(price_str, str):
        # Remove currency symbols, commas, whitespace
        cleaned = price_str.replace("$", "").replace(",", "").replace("€", "").replace("£", "").strip()
        try:
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0
    
    return 0.0


def normalize_condition(condition_str: Any) -> str:
    """
    Normalize condition strings to standard values.
    """
    if not condition_str:
        return "Unknown"
    
    condition_lower = str(condition_str).lower()
    
    # Map common variations
    if any(word in condition_lower for word in ["new", "brand new", "unused"]):
        return "New"
    elif any(word in condition_lower for word in ["used", "pre-owned", "second hand"]):
        return "Used"
    elif any(word in condition_str.lower() for word in ["refurbished", "reconditioned"]):
        return "Refurbished"
    elif any(word in condition_lower for word in ["salvage", "wrecked", "parts only"]):
        return "Salvage"
    else:
        return str(condition_str).title()


def clean_url(url: str) -> str:
    """
    Clean and validate URL.
    """
    if not url:
        return ""
    
    url = url.strip()
    
    # Ensure it starts with http:// or https://
    if url and not url.startswith(("http://", "https://")):
        # If it's a relative URL, we might want to handle it differently
        # For now, assume it needs https://
        if url.startswith("/"):
            # This is a relative URL - we'd need base URL context
            pass
        else:
            url = f"https://{url}"
    
    return url
