"""Tests for ranking and sorting utilities."""

from app.schemas.search import ExternalLink, MarketListing, SalvageHit
from app.services.ai_advisor import AIAdvisorResult
from app.utils.query_analysis import QueryAnalysis, QueryType
from app.utils.ranking import filter_market_listings, filter_salvage_hits, group_links_by_category, rank_listings


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


class TestFilterMarketListings:
    def test_wrong_model_filtered(self):
        """Listings for wrong model of same make are filtered out."""
        ai = AIAdvisorResult(vehicle_make="Porsche", vehicle_model="944")
        listings = [
            _make_listing(title="Porsche 911 Engine Mount", url="https://example.com/1"),
            _make_listing(title="Porsche 944 Engine Mount", url="https://example.com/2"),
            _make_listing(title="Porsche Cayenne Motor Mount", url="https://example.com/3"),
        ]
        result = filter_market_listings(listings, ai)
        assert len(result) == 1
        assert "944" in result[0].title

    def test_generic_parts_kept(self):
        """Listings mentioning make but no specific model are kept."""
        ai = AIAdvisorResult(vehicle_make="Porsche", vehicle_model="944")
        listings = [
            _make_listing(title="Porsche Engine Mount Universal", url="https://example.com/1"),
            _make_listing(title="Engine Mount - Fits Porsche", url="https://example.com/2"),
        ]
        result = filter_market_listings(listings, ai)
        assert len(result) == 2

    def test_generic_no_make_kept(self):
        """Listings not mentioning any known make are kept (generic/universal)."""
        ai = AIAdvisorResult(vehicle_make="Porsche", vehicle_model="944")
        listings = [
            _make_listing(title="Universal Engine Mount Bracket", url="https://example.com/1"),
            _make_listing(title="Engine Mount Heavy Duty Replacement", url="https://example.com/2"),
        ]
        result = filter_market_listings(listings, ai)
        assert len(result) == 2

    def test_cross_make_filtered(self):
        """Listings mentioning a different make are filtered when searching a specific vehicle."""
        ai = AIAdvisorResult(vehicle_make="Porsche", vehicle_model="944")
        listings = [
            _make_listing(title="BMW E36 Engine Mount", url="https://example.com/1"),
            _make_listing(title="Audi A5 Engine Mount", url="https://example.com/2"),
            _make_listing(title="Porsche 944 Engine Mount", url="https://example.com/3"),
        ]
        result = filter_market_listings(listings, ai)
        assert len(result) == 1
        assert "Porsche 944" in result[0].title

    def test_short_make_word_boundary(self):
        """Short make names like 'kia' use word boundaries to avoid false positives."""
        ai = AIAdvisorResult(vehicle_make="Porsche", vehicle_model="944")
        listings = [
            # "kia" appears as a word — should be filtered
            _make_listing(title="Kia Sportage Engine Mount", url="https://example.com/1"),
            # "kia" is part of another word — should NOT be filtered
            _make_listing(title="Akia Brand Engine Mount", url="https://example.com/2"),
        ]
        result = filter_market_listings(listings, ai)
        assert len(result) == 1
        assert "Akia" in result[0].title

    def test_no_make_wrong_pn_filtered(self):
        """Listings with no make but non-matching part numbers are filtered when OEM PNs known."""
        ai = AIAdvisorResult(
            vehicle_make="Porsche",
            vehicle_model="944",
            oem_part_numbers=["94437504105", "94437504107"],
        )
        listings = [
            # Audi PN, no make mentioned — should be filtered
            _make_listing(
                title="URO Parts 8R0199381C Engine Mount",
                url="https://example.com/1",
                part_numbers=["8R0199381C"],
            ),
            # Matching OEM PN — should be kept
            _make_listing(
                title="Engine Mount 94437504105",
                url="https://example.com/2",
                part_numbers=["94437504105"],
            ),
            # No extracted PNs but title contains OEM PN — kept
            _make_listing(title="Engine Mount 94437504105 Replacement", url="https://example.com/3"),
            # No PNs and no OEM PN in title — filtered
            _make_listing(title="Engine Mount Universal", url="https://example.com/4"),
        ]
        result = filter_market_listings(listings, ai)
        assert len(result) == 2
        titles = [r.title for r in result]
        assert "URO Parts 8R0199381C Engine Mount" not in titles
        assert "Engine Mount 94437504105" in titles
        assert "Engine Mount 94437504105 Replacement" in titles
        assert "Engine Mount Universal" not in titles

    def test_no_make_wrong_pn_kept_without_model(self):
        """No-make filtering only applies when AI has both make AND model."""
        ai = AIAdvisorResult(
            vehicle_make="Porsche",
            oem_part_numbers=["94437504105"],
        )
        listings = [
            _make_listing(
                title="URO Parts 8R0199381C Engine Mount",
                url="https://example.com/1",
                part_numbers=["8R0199381C"],
            ),
        ]
        result = filter_market_listings(listings, ai)
        assert len(result) == 1  # No model = no stage 3 filtering

    def test_known_part_numbers_from_caller(self):
        """Caller-provided part numbers (interchange/extracted) also match in stage 3."""
        ai = AIAdvisorResult(vehicle_make="Porsche", vehicle_model="944")
        listings = [
            _make_listing(
                title="Engine Mount IC-12345",
                url="https://example.com/1",
                part_numbers=["IC-12345"],
            ),
        ]
        # IC-12345 not in AI OEM PNs, but passed via known_part_numbers
        result = filter_market_listings(listings, ai, known_part_numbers=["IC-12345"])
        assert len(result) == 1

    def test_no_ai_hint_passes_all(self):
        """All listings pass when no AI analysis is available."""
        listings = [
            _make_listing(title="Porsche 911 Engine Mount", url="https://example.com/1"),
            _make_listing(title="Porsche 944 Engine Mount", url="https://example.com/2"),
        ]
        result = filter_market_listings(listings, None)
        assert len(result) == 2

    def test_both_models_kept(self):
        """Listing mentioning both target and another model is kept."""
        ai = AIAdvisorResult(vehicle_make="Porsche", vehicle_model="944")
        listings = [
            _make_listing(title="Porsche 944 924 Engine Mount", url="https://example.com/1"),
        ]
        result = filter_market_listings(listings, ai)
        assert len(result) == 1

    def test_no_vehicle_model_passes_all(self):
        """All listings pass when AI has make but no model."""
        ai = AIAdvisorResult(vehicle_make="Porsche")
        listings = [
            _make_listing(title="Porsche 911 Engine Mount", url="https://example.com/1"),
        ]
        result = filter_market_listings(listings, ai)
        assert len(result) == 1
