"""Tests for ranking and sorting utilities."""

from app.schemas.search import ExternalLink, MarketListing, SalvageHit
from app.utils.query_analysis import QueryAnalysis, QueryType
from app.utils.ranking import filter_salvage_hits, group_links_by_category, rank_listings


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


def _make_salvage_hit(**kwargs):
    defaults = {
        "source": "row52",
        "yard_name": "Test Yard",
        "yard_location": "Test, CA",
        "vehicle": "2015 Honda Civic",
        "url": "https://example.com",
    }
    defaults.update(kwargs)
    return SalvageHit(**defaults)


class TestContextAwareRanking:
    def test_part_number_match_boosts_score(self):
        """Listing with a matching part number scores higher when analysis has that part number."""
        analysis = QueryAnalysis(
            query_type=QueryType.PART_NUMBER,
            original_query="BP1234",
            part_numbers=["BP1234"],
        )
        listings = [
            _make_listing(title="Generic Brake Pad", url="https://example.com/1"),
            _make_listing(title="Brake Pad BP1234", url="https://example.com/2", part_numbers=["BP1234"]),
        ]
        result = rank_listings(listings, "BP1234", "relevance", analysis)
        assert result[0].part_numbers == ["BP1234"]

    def test_vehicle_hint_match_boosts_score(self):
        """Listing matching the vehicle_hint scores higher."""
        analysis = QueryAnalysis(
            query_type=QueryType.VEHICLE_PART,
            original_query="2015 Honda Civic brake pads",
            vehicle_hint="2015 Honda Civic",
        )
        listings = [
            _make_listing(title="Brake Pads for Toyota Camry", url="https://example.com/1"),
            _make_listing(title="Brake Pads 2015 Honda Civic", url="https://example.com/2"),
        ]
        result = rank_listings(listings, "brake pads", "relevance", analysis)
        assert "Honda Civic" in result[0].title

    def test_part_description_match_boosts_score(self):
        """Listing matching part_description scores higher."""
        analysis = QueryAnalysis(
            query_type=QueryType.KEYWORDS,
            original_query="ceramic brake pads",
            part_description="ceramic brake pads",
        )
        listings = [
            _make_listing(title="Standard Oil Filter", url="https://example.com/1"),
            _make_listing(title="Ceramic Brake Pads Premium", url="https://example.com/2"),
        ]
        result = rank_listings(listings, "ceramic brake pads", "relevance", analysis)
        assert "Ceramic Brake Pads" in result[0].title

    def test_brand_match_boosts_score(self):
        """Brand match gives a boost when analysis has brands_found."""
        analysis = QueryAnalysis(
            query_type=QueryType.KEYWORDS,
            original_query="Bosch brake pads",
            brands_found=["Bosch"],
        )
        listings = [
            _make_listing(title="Brake Pads", url="https://example.com/1", brand="Wagner"),
            _make_listing(title="Brake Pads", url="https://example.com/2", brand="Bosch"),
        ]
        result = rank_listings(listings, "brake pads", "relevance", analysis)
        assert result[0].brand == "Bosch"


class TestFilterSalvageHits:
    def test_filters_wrong_vehicle_make(self):
        """Salvage hits for wrong vehicle make are filtered out when vehicle_hint is set."""
        analysis = QueryAnalysis(
            query_type=QueryType.VEHICLE_PART,
            original_query="Honda Civic brake pads",
            vehicle_hint="Honda Civic",
        )
        hits = [
            _make_salvage_hit(vehicle="2015 Honda Civic", url="https://example.com/1"),
            _make_salvage_hit(vehicle="2018 Toyota Camry", url="https://example.com/2"),
            _make_salvage_hit(vehicle="2020 Kia Sedona", url="https://example.com/3"),
        ]
        result = filter_salvage_hits(hits, analysis)
        assert len(result) == 1
        assert "Honda" in result[0].vehicle

    def test_keeps_correct_vehicle_make(self):
        """Salvage hits for correct vehicle make are kept."""
        analysis = QueryAnalysis(
            query_type=QueryType.VEHICLE_PART,
            original_query="2015 Honda Civic",
            vehicle_hint="2015 Honda Civic",
        )
        hits = [
            _make_salvage_hit(vehicle="2015 Honda Civic", url="https://example.com/1"),
            _make_salvage_hit(vehicle="2012 Honda Accord", url="https://example.com/2"),
        ]
        result = filter_salvage_hits(hits, analysis)
        assert len(result) == 2

    def test_no_vehicle_hint_passes_all(self):
        """All hits pass through when no vehicle_hint is set."""
        analysis = QueryAnalysis(
            query_type=QueryType.KEYWORDS,
            original_query="brake pads",
        )
        hits = [
            _make_salvage_hit(vehicle="2015 Honda Civic", url="https://example.com/1"),
            _make_salvage_hit(vehicle="2018 Toyota Camry", url="https://example.com/2"),
        ]
        result = filter_salvage_hits(hits, analysis)
        assert len(result) == 2

    def test_empty_vehicle_field_kept(self):
        """Hits with empty vehicle field are kept even when vehicle_hint is set."""
        analysis = QueryAnalysis(
            query_type=QueryType.VEHICLE_PART,
            original_query="Porsche 944 brake pads",
            vehicle_hint="Porsche 944",
        )
        hits = [
            _make_salvage_hit(vehicle="2018 Toyota Camry", url="https://example.com/1"),
            _make_salvage_hit(vehicle="", url="https://example.com/2"),
            _make_salvage_hit(vehicle="1987 Porsche 944", url="https://example.com/3"),
        ]
        result = filter_salvage_hits(hits, analysis)
        assert len(result) == 2
        vehicles = [h.vehicle for h in result]
        assert "" in vehicles
        assert "1987 Porsche 944" in vehicles
