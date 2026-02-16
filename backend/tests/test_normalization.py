"""Tests for price, condition, and URL normalization."""

from app.utils.normalization import clean_url, normalize_condition, normalize_price


class TestNormalizePrice:
    def test_string_with_dollar(self):
        assert normalize_price("$42.99") == 42.99

    def test_string_plain(self):
        assert normalize_price("42.99") == 42.99

    def test_string_with_comma(self):
        assert normalize_price("1,234.56") == 1234.56

    def test_int(self):
        assert normalize_price(42) == 42.0

    def test_float(self):
        assert normalize_price(42.99) == 42.99

    def test_none(self):
        assert normalize_price(None) == 0.0

    def test_invalid_string(self):
        assert normalize_price("free") == 0.0

    def test_euro_symbol(self):
        assert normalize_price("€49.99") == 49.99


class TestNormalizeCondition:
    def test_new(self):
        assert normalize_condition("Brand New") == "New"

    def test_used(self):
        assert normalize_condition("Pre-Owned") == "Used"

    def test_refurbished(self):
        assert normalize_condition("Refurbished") == "Refurbished"

    def test_salvage(self):
        assert normalize_condition("Parts Only") == "Salvage"

    def test_unknown(self):
        assert normalize_condition("") == "Unknown"
        assert normalize_condition(None) == "Unknown"

    def test_other(self):
        result = normalize_condition("Like New")
        assert isinstance(result, str)


class TestCleanUrl:
    def test_already_https(self):
        assert clean_url("https://example.com") == "https://example.com"

    def test_already_http(self):
        assert clean_url("http://example.com") == "http://example.com"

    def test_no_scheme(self):
        assert clean_url("example.com") == "https://example.com"

    def test_empty(self):
        assert clean_url("") == ""

    def test_whitespace(self):
        assert clean_url("  https://example.com  ") == "https://example.com"
