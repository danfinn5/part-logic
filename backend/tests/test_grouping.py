"""Tests for listing grouping and price comparison."""

from app.schemas.search import MarketListing
from app.utils.grouping import group_listings, sort_groups


def _make_listing(**kwargs) -> MarketListing:
    defaults = {
        "source": "rockauto",
        "title": "Bosch QuietCast BP1234 Brake Pad Set",
        "price": 32.49,
        "url": "https://rockauto.com/bp1234",
        "part_numbers": ["BP1234"],
        "brand": "Bosch",
    }
    defaults.update(kwargs)
    return MarketListing(**defaults)


class TestGroupListings:
    def test_groups_same_brand_and_part_number(self):
        listings = [
            _make_listing(source="rockauto", price=32.49, url="https://rockauto.com/1"),
            _make_listing(source="amazon", price=38.99, url="https://amazon.com/1"),
            _make_listing(source="fcpeuro", price=41.50, url="https://fcpeuro.com/1"),
        ]
        groups = group_listings(listings)
        assert len(groups) == 1
        assert groups[0]["brand"] == "Bosch"
        assert groups[0]["part_number"] == "BP1234"
        assert groups[0]["offer_count"] == 3
        assert groups[0]["best_price"] == 32.49

    def test_different_brands_create_separate_groups(self):
        listings = [
            _make_listing(brand="Bosch", part_numbers=["BP1234"], price=32.0),
            _make_listing(brand="Wagner", part_numbers=["PD1234"], price=28.0, url="https://other.com"),
        ]
        groups = group_listings(listings)
        assert len(groups) == 2

    def test_different_part_numbers_same_brand_separate_groups(self):
        listings = [
            _make_listing(brand="Bosch", part_numbers=["BP1234"], price=32.0),
            _make_listing(brand="Bosch", part_numbers=["BP5678"], price=28.0, url="https://other.com"),
        ]
        groups = group_listings(listings)
        assert len(groups) == 2

    def test_ungrouped_listings_no_brand(self):
        listings = [
            _make_listing(brand=None, part_numbers=["BP1234"], price=25.0),
        ]
        groups = group_listings(listings)
        assert len(groups) == 1
        assert groups[0]["brand"] == "Unknown"
        assert groups[0]["offer_count"] == 1

    def test_ungrouped_listings_no_part_numbers(self):
        listings = [
            _make_listing(brand="Bosch", part_numbers=[], price=25.0),
        ]
        groups = group_listings(listings)
        assert len(groups) == 1
        assert groups[0]["offer_count"] == 1

    def test_zero_price_excluded(self):
        listings = [
            _make_listing(price=0.0),
            _make_listing(price=32.49, url="https://other.com"),
        ]
        groups = group_listings(listings)
        total_offers = sum(g["offer_count"] for g in groups)
        assert total_offers == 1

    def test_offers_sorted_by_total_cost(self):
        listings = [
            _make_listing(source="expensive", price=50.0, shipping_cost=0, url="https://a.com"),
            _make_listing(source="cheap", price=30.0, shipping_cost=5.0, url="https://b.com"),
            _make_listing(source="mid", price=40.0, shipping_cost=0, url="https://c.com"),
        ]
        groups = group_listings(listings)
        assert len(groups) == 1
        offers = groups[0]["offers"]
        assert offers[0]["source"] == "cheap"  # 35.0 total
        assert offers[1]["source"] == "mid"  # 40.0 total
        assert offers[2]["source"] == "expensive"  # 50.0 total

    def test_shipping_included_in_total_cost(self):
        listings = [
            _make_listing(price=30.0, shipping_cost=10.0),
        ]
        groups = group_listings(listings)
        assert groups[0]["offers"][0]["total_cost"] == 40.0

    def test_value_score_computed(self):
        listings = [
            _make_listing(price=32.49),
        ]
        groups = group_listings(listings)
        assert groups[0]["best_value_score"] > 0


class TestSortGroups:
    def _make_groups(self):
        return [
            {"best_price": 50.0, "best_value_score": 1.5, "quality_score": 9.0},
            {"best_price": 30.0, "best_value_score": 2.5, "quality_score": 7.0},
            {"best_price": 40.0, "best_value_score": 2.0, "quality_score": 5.0},
        ]

    def test_sort_by_value(self):
        groups = self._make_groups()
        result = sort_groups(groups, "value")
        assert result[0]["best_value_score"] == 2.5

    def test_sort_by_price_asc(self):
        groups = self._make_groups()
        result = sort_groups(groups, "price_asc")
        assert result[0]["best_price"] == 30.0

    def test_sort_by_price_desc(self):
        groups = self._make_groups()
        result = sort_groups(groups, "price_desc")
        assert result[0]["best_price"] == 50.0

    def test_sort_by_quality(self):
        groups = self._make_groups()
        result = sort_groups(groups, "quality")
        assert result[0]["quality_score"] == 9.0
