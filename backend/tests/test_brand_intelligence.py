"""Tests for the brand intelligence module."""

from app.data.brand_knowledge import get_brand_profile, get_brand_tier
from app.schemas.search import MarketListing
from app.utils.brand_intelligence import (
    build_brand_comparison,
    get_brand_tier_boost,
)
from app.utils.interchange import InterchangeGroup


class TestGetBrandProfile:
    def test_direct_match(self):
        profile = get_brand_profile("Lemforder")
        assert profile is not None
        assert profile["tier"] == "premium_aftermarket"

    def test_case_insensitive(self):
        profile = get_brand_profile("lemforder")
        assert profile is not None
        assert profile["tier"] == "premium_aftermarket"

    def test_unknown_brand(self):
        profile = get_brand_profile("UnknownBrand123")
        assert profile is None

    def test_get_tier(self):
        assert get_brand_tier("Lemforder") == "premium_aftermarket"
        assert get_brand_tier("URO") == "budget"
        assert get_brand_tier("UnknownBrand") == "unknown"


class TestBuildBrandComparison:
    def _make_listing(self, brand: str, price: float, source: str = "ebay") -> MarketListing:
        return MarketListing(
            source=source,
            title=f"{brand} Engine Mount",
            price=price,
            url="https://example.com/item",
            brand=brand,
        )

    def test_groups_by_brand(self):
        listings = [
            self._make_listing("Lemforder", 89.99),
            self._make_listing("Lemforder", 92.50),
            self._make_listing("Meyle", 64.99),
            self._make_listing("URO", 29.99),
        ]
        result = build_brand_comparison(listings)

        assert len(result) == 3
        brands = {s.brand for s in result}
        assert "Lemforder" in brands
        assert "Meyle" in brands
        assert "Uro" in brands

    def test_computes_avg_price(self):
        listings = [
            self._make_listing("Lemforder", 80.00),
            self._make_listing("Lemforder", 100.00),
        ]
        result = build_brand_comparison(listings)

        lemforder = next(s for s in result if s.brand == "Lemforder")
        assert lemforder.avg_price == 90.00
        assert lemforder.listing_count == 2

    def test_includes_tier_and_quality(self):
        listings = [self._make_listing("Bosch", 50.00)]
        result = build_brand_comparison(listings)

        bosch = result[0]
        assert bosch.tier == "premium_aftermarket"
        assert bosch.quality_score > 0

    def test_unknown_brand_gets_defaults(self):
        listings = [self._make_listing("MysteryBrand", 25.00)]
        result = build_brand_comparison(listings)

        assert len(result) == 1
        assert result[0].tier == "unknown"
        assert result[0].quality_score == 0.0

    def test_sorted_by_tier_and_quality(self):
        listings = [
            self._make_listing("URO", 29.99),
            self._make_listing("Lemforder", 89.99),
            self._make_listing("Meyle", 64.99),
        ]
        result = build_brand_comparison(listings)

        # Premium should come before economy, which comes before budget
        tiers = [s.tier for s in result]
        assert tiers.index("premium_aftermarket") < tiers.index("economy")

    def test_empty_listings(self):
        result = build_brand_comparison([])
        assert result == []

    def test_listings_without_brand_skipped(self):
        listings = [
            MarketListing(
                source="ebay",
                title="Engine Mount",
                price=50.00,
                url="https://example.com",
                brand=None,
            )
        ]
        result = build_brand_comparison(listings)
        assert result == []

    def test_includes_interchange_brands(self):
        listings = [self._make_listing("Lemforder", 89.99)]
        interchange = InterchangeGroup(
            primary_part_number="TEST",
            brands={"Meyle": ["DEF456"], "Sachs": ["GHI789"]},
        )
        result = build_brand_comparison(listings, interchange=interchange)

        brands = {s.brand for s in result}
        assert "Meyle" in brands
        assert "Sachs" in brands
        # Brands from interchange without listings should have 0 count
        meyle = next(s for s in result if s.brand == "Meyle")
        assert meyle.listing_count == 0
        assert meyle.avg_price is None

    def test_recommendation_notes_generated(self):
        listings = [
            self._make_listing("Lemforder", 89.99),
            self._make_listing("URO", 29.99),
        ]
        result = build_brand_comparison(listings)

        lemforder = next(s for s in result if s.brand == "Lemforder")
        uro = next(s for s in result if s.brand == "Uro")
        assert lemforder.recommendation_note is not None
        assert uro.recommendation_note is not None

    def test_zero_price_excluded_from_avg(self):
        listings = [
            self._make_listing("Bosch", 50.00),
            self._make_listing("Bosch", 0.00),  # should be excluded
        ]
        result = build_brand_comparison(listings)

        bosch = next(s for s in result if s.brand == "Bosch")
        assert bosch.avg_price == 50.00
        assert bosch.listing_count == 2


class TestGetBrandTierBoost:
    def test_premium_boost_for_part_number(self):
        boost = get_brand_tier_boost("Lemforder", "part_number")
        assert boost > 0

    def test_oem_highest_boost(self):
        oem_boost = get_brand_tier_boost("Motorcraft", "part_number")
        premium_boost = get_brand_tier_boost("Lemforder", "part_number")
        assert oem_boost > premium_boost

    def test_budget_no_boost(self):
        boost = get_brand_tier_boost("URO", "part_number")
        assert boost == 0.0

    def test_unknown_brand_no_boost(self):
        boost = get_brand_tier_boost("MysteryBrand", "part_number")
        assert boost == 0.0

    def test_smaller_boosts_for_keywords(self):
        pn_boost = get_brand_tier_boost("Lemforder", "part_number")
        kw_boost = get_brand_tier_boost("Lemforder", "keywords")
        assert pn_boost > kw_boost
