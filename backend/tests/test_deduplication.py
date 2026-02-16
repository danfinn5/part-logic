"""Tests for deduplication utilities."""

from app.schemas.search import ExternalLink, MarketListing
from app.utils.deduplication import deduplicate_links, deduplicate_listings


class TestDeduplicateListings:
    def test_removes_duplicate_urls(self):
        listings = [
            MarketListing(source="ebay", title="Part A", price=10.0, url="https://ebay.com/1"),
            MarketListing(source="ebay", title="Part A copy", price=10.0, url="https://ebay.com/1"),
            MarketListing(source="ebay", title="Part B", price=20.0, url="https://ebay.com/2"),
        ]
        result = deduplicate_listings(listings)
        assert len(result) == 2
        assert result[0].title == "Part A"
        assert result[1].title == "Part B"

    def test_keeps_different_urls(self):
        listings = [
            MarketListing(source="ebay", title="Part A", price=10.0, url="https://ebay.com/1"),
            MarketListing(source="ebay", title="Part B", price=20.0, url="https://ebay.com/2"),
        ]
        result = deduplicate_listings(listings)
        assert len(result) == 2

    def test_empty_input(self):
        assert deduplicate_listings([]) == []


class TestDeduplicateLinks:
    def test_removes_duplicate_source_url_pairs(self):
        links = [
            ExternalLink(label="A", url="https://example.com/1", source="rockauto"),
            ExternalLink(label="A again", url="https://example.com/1", source="rockauto"),
            ExternalLink(label="B", url="https://example.com/2", source="rockauto"),
        ]
        result = deduplicate_links(links)
        assert len(result) == 2

    def test_same_url_different_source_kept(self):
        links = [
            ExternalLink(label="A", url="https://example.com/1", source="rockauto"),
            ExternalLink(label="A", url="https://example.com/1", source="partsgeek"),
        ]
        result = deduplicate_links(links)
        assert len(result) == 2

    def test_empty_input(self):
        assert deduplicate_links([]) == []
