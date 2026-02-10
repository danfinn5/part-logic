"""
Deduplication utilities for search results.
"""
from typing import List
from app.schemas.search import MarketListing, ExternalLink


def deduplicate_listings(listings: List[MarketListing]) -> List[MarketListing]:
    """Deduplicate MarketListing results by URL."""
    seen_urls: set = set()
    unique: List[MarketListing] = []
    for listing in listings:
        if listing.url not in seen_urls:
            seen_urls.add(listing.url)
            unique.append(listing)
    return unique


def deduplicate_links(links: List[ExternalLink]) -> List[ExternalLink]:
    """Deduplicate ExternalLink results by (source, url) pair."""
    seen: set = set()
    unique: List[ExternalLink] = []
    for link in links:
        key = (link.source, link.url)
        if key not in seen:
            seen.add(key)
            unique.append(link)
    return unique
