"""
Deduplication utilities for search results.
"""

from app.schemas.search import ExternalLink, MarketListing


def deduplicate_listings(listings: list[MarketListing]) -> list[MarketListing]:
    """Deduplicate MarketListing results by URL."""
    seen_urls: set = set()
    unique: list[MarketListing] = []
    for listing in listings:
        if listing.url not in seen_urls:
            seen_urls.add(listing.url)
            unique.append(listing)
    return unique


def deduplicate_links(links: list[ExternalLink]) -> list[ExternalLink]:
    """Deduplicate ExternalLink results by (source, url) pair."""
    seen: set = set()
    unique: list[ExternalLink] = []
    for link in links:
        key = (link.source, link.url)
        if key not in seen:
            seen.add(key)
            unique.append(link)
    return unique
