"""Tests for ranking and sorting utilities."""
from app.utils.ranking import rank_listings, group_links_by_category
from app.schemas.search import MarketListing, ExternalLink


def _make_listing(**kwargs):
    defaults = {"source": "ebay", "title": "Part", "price": 10.0, "url": "https://example.com"}
    defaults.update(kwargs)
    return MarketListing(**defaults)


class TestRankListings:
    def test_relevance_prefers_title_match(self):
        listings = [
            _make_listing(title="Unrelated Widget", url="https://example.com/1"),
            _make_listing(title="Brake Pads Ceramic", url="https://example.com/2"),
        ]
        result = rank_listings(listings, "BRAKE PADS", "relevance")
        assert result[0].title == "Brake Pads Ceramic"

    def test_relevance_prefers_with_image(self):
        listings = [
            _make_listing(title="Brake Pads", url="https://example.com/1"),
            _make_listing(title="Brake Pads", url="https://example.com/2", image_url="https://img.com/1.jpg"),
        ]
        result = rank_listings(listings, "BRAKE PADS", "relevance")
        assert result[0].image_url is not None

    def test_price_asc(self):
        listings = [
            _make_listing(title="Expensive", price=100.0, url="https://example.com/1"),
            _make_listing(title="Cheap", price=10.0, url="https://example.com/2"),
        ]
        result = rank_listings(listings, "part", "price_asc")
        assert result[0].price == 10.0
        assert result[1].price == 100.0

    def test_price_desc(self):
        listings = [
            _make_listing(title="Cheap", price=10.0, url="https://example.com/1"),
            _make_listing(title="Expensive", price=100.0, url="https://example.com/2"),
        ]
        result = rank_listings(listings, "part", "price_desc")
        assert result[0].price == 100.0

    def test_zero_price_sorted_last_in_price_asc(self):
        listings = [
            _make_listing(title="Free", price=0.0, url="https://example.com/1"),
            _make_listing(title="Paid", price=5.0, url="https://example.com/2"),
        ]
        result = rank_listings(listings, "part", "price_asc")
        assert result[0].price == 5.0

    def test_empty_input(self):
        assert rank_listings([], "query", "relevance") == []


class TestGroupLinksByCategory:
    def test_groups_in_order(self):
        links = [
            ExternalLink(label="YouTube", url="https://youtube.com", source="youtube", category="repair_resources"),
            ExternalLink(label="Car-Part", url="https://car-part.com", source="carpart", category="used_salvage"),
            ExternalLink(label="RockAuto", url="https://rockauto.com", source="rockauto", category="new_parts"),
        ]
        result = group_links_by_category(links)
        assert result[0].category == "new_parts"
        assert result[1].category == "used_salvage"
        assert result[2].category == "repair_resources"

    def test_empty_input(self):
        assert group_links_by_category([]) == []
