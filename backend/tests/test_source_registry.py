"""Tests for source registry: import, normalization, tags, upsert, filtering."""

from unittest import mock

import pytest

from app.data.source_registry import (
    get_active_sources,
    get_all_sources,
    get_registry_stats,
    get_source,
    normalize_domain,
    parse_tags,
    set_source_priority,
    toggle_source_status,
    upsert_source,
)


# Use a temp file for registry during tests so we don't corrupt the real one
@pytest.fixture(autouse=True)
def temp_registry(tmp_path):
    temp_file = tmp_path / "test_sources.json"
    with mock.patch("app.data.source_registry._REGISTRY_PATH", temp_file):
        yield temp_file


# ─── Domain Normalization ────────────────────────────────────────────


class TestNormalizeDomain:
    def test_basic(self):
        assert normalize_domain("rockauto.com") == "rockauto.com"

    def test_uppercase(self):
        assert normalize_domain("RockAuto.COM") == "rockauto.com"

    def test_strip_scheme(self):
        assert normalize_domain("https://www.rockauto.com") == "rockauto.com"

    def test_strip_www(self):
        assert normalize_domain("www.ebay.com") == "ebay.com"

    def test_strip_trailing_slash(self):
        assert normalize_domain("ebay.com/") == "ebay.com"

    def test_preserve_meaningful_path(self):
        assert normalize_domain("facebook.com/marketplace") == "facebook.com/marketplace"

    def test_full_url_with_path(self):
        assert normalize_domain("https://www.facebook.com/marketplace/") == "facebook.com/marketplace"

    def test_whitespace(self):
        assert normalize_domain("  ebay.com  ") == "ebay.com"

    def test_subdomain_preserved(self):
        assert normalize_domain("parts.ford.com") == "parts.ford.com"

    def test_epc_subdomain(self):
        assert normalize_domain("toyota.epc-data.com") == "toyota.epc-data.com"


# ─── Tag Parsing ─────────────────────────────────────────────────────


class TestParseTags:
    def test_basic(self):
        assert parse_tags("new_aftermarket,wide_catalog") == ["new_aftermarket", "wide_catalog"]

    def test_with_spaces(self):
        assert parse_tags(" euro , performance , new_aftermarket ") == [
            "euro",
            "new_aftermarket",
            "performance",
        ]

    def test_empty(self):
        assert parse_tags("") == []
        assert parse_tags("   ") == []

    def test_deduplication(self):
        assert parse_tags("bmw,euro,bmw") == ["bmw", "euro"]

    def test_sorted(self):
        tags = parse_tags("zzz,aaa,mmm")
        assert tags == ["aaa", "mmm", "zzz"]

    def test_lowercase(self):
        assert parse_tags("BMW,Euro") == ["bmw", "euro"]


# ─── Upsert ──────────────────────────────────────────────────────────


class TestUpsert:
    def test_insert_new_source(self):
        source = upsert_source(
            domain="test.com",
            name="Test Source",
            category="retailer",
            tags=["new_aftermarket"],
        )
        assert source["domain"] == "test.com"
        assert source["name"] == "Test Source"
        assert source["status"] == "active"
        assert source["priority"] == 50
        assert source["id"]  # UUID assigned
        assert source["created_at"]

    def test_upsert_no_duplicate(self):
        """Re-importing the same domain updates, doesn't duplicate."""
        upsert_source(domain="dupe.com", name="First", category="retailer", tags=[])
        upsert_source(domain="dupe.com", name="Updated", category="marketplace", tags=["new"])

        all_sources = get_all_sources()
        matches = [s for s in all_sources if s["domain"] == "dupe.com"]
        assert len(matches) == 1
        assert matches[0]["name"] == "Updated"
        assert matches[0]["category"] == "marketplace"
        assert matches[0]["tags"] == ["new"]

    def test_upsert_preserves_id(self):
        s1 = upsert_source(domain="stable.com", name="V1", category="retailer", tags=[])
        s2 = upsert_source(domain="stable.com", name="V2", category="retailer", tags=[])
        assert s1["id"] == s2["id"]

    def test_domain_normalization_on_upsert(self):
        upsert_source(domain="https://www.Example.COM/", name="Ex", category="retailer", tags=[])
        source = get_source("example.com")
        assert source is not None
        assert source["name"] == "Ex"

    def test_default_crawler_hints(self):
        source = upsert_source(domain="hints.com", name="H", category="retailer", tags=[])
        assert source["supports_vin"] is False
        assert source["supports_part_number_search"] is True
        assert source["robots_policy"] == "unknown"
        assert source["sitemap_url"] is None


# ─── Toggle Status ───────────────────────────────────────────────────


class TestToggleStatus:
    def test_toggle_active_to_disabled(self):
        upsert_source(domain="toggle.com", name="T", category="retailer", tags=[])
        result = toggle_source_status("toggle.com")
        assert result["status"] == "disabled"

    def test_toggle_disabled_to_active(self):
        upsert_source(domain="toggle2.com", name="T", category="retailer", tags=[], status="disabled")
        result = toggle_source_status("toggle2.com")
        assert result["status"] == "active"

    def test_toggle_nonexistent(self):
        result = toggle_source_status("nope.com")
        assert result is None


# ─── Filtering ───────────────────────────────────────────────────────


class TestFiltering:
    def setup_method(self):
        upsert_source(domain="a.com", name="A", category="retailer", tags=["euro"], source_type="buyable")
        upsert_source(domain="b.com", name="B", category="marketplace", tags=["used"], source_type="buyable")
        upsert_source(domain="c.com", name="C", category="epc", tags=["bmw"], source_type="reference")
        upsert_source(
            domain="d.com", name="D", category="retailer", tags=["euro"], source_type="buyable", status="disabled"
        )

    def test_filter_by_source_type(self):
        results = get_active_sources(source_type="buyable")
        domains = {s["domain"] for s in results}
        assert "a.com" in domains
        assert "b.com" in domains
        assert "c.com" not in domains

    def test_filter_by_category(self):
        results = get_active_sources(category="retailer")
        domains = {s["domain"] for s in results}
        assert "a.com" in domains
        assert "b.com" not in domains

    def test_filter_by_tag(self):
        results = get_active_sources(tag="euro")
        domains = {s["domain"] for s in results}
        assert "a.com" in domains
        assert "b.com" not in domains

    def test_disabled_excluded(self):
        results = get_active_sources()
        domains = {s["domain"] for s in results}
        assert "d.com" not in domains


# ─── Priority ────────────────────────────────────────────────────────


class TestPriority:
    def test_set_priority(self):
        upsert_source(domain="pri.com", name="P", category="retailer", tags=[])
        result = set_source_priority("pri.com", 99)
        assert result["priority"] == 99

    def test_priority_ordering(self):
        upsert_source(domain="low.com", name="Low", category="retailer", tags=[], priority=10)
        upsert_source(domain="high.com", name="High", category="retailer", tags=[], priority=90)
        all_s = get_all_sources()
        domains = [s["domain"] for s in all_s]
        assert domains.index("high.com") < domains.index("low.com")


# ─── Stats ───────────────────────────────────────────────────────────


class TestStats:
    def test_stats(self):
        upsert_source(domain="s1.com", name="S1", category="retailer", tags=[], source_type="buyable")
        upsert_source(domain="s2.com", name="S2", category="epc", tags=[], source_type="reference")
        upsert_source(
            domain="s3.com", name="S3", category="retailer", tags=[], source_type="buyable", status="disabled"
        )

        stats = get_registry_stats()
        assert stats["total"] == 3
        assert stats["active"] == 2
        assert stats["disabled"] == 1
        assert stats["by_source_type"]["buyable"] == 2
        assert stats["by_source_type"]["reference"] == 1
        assert stats["by_category"]["retailer"] == 2
