"""Tests for shared scraping utilities."""

from app.utils.scraping import default_headers, get_random_ua, parse_price


class TestParsePrice:
    def test_dollar_amount(self):
        assert parse_price("$42.99") == 42.99

    def test_dollar_with_comma(self):
        assert parse_price("$1,234.56") == 1234.56

    def test_plain_number(self):
        assert parse_price("29.99") == 29.99

    def test_euro_symbol(self):
        assert parse_price("€49.99") == 49.99

    def test_whitespace_and_newlines(self):
        assert parse_price("  \n$42.99\t ") == 42.99

    def test_empty_string(self):
        assert parse_price("") == 0.0

    def test_none(self):
        assert parse_price(None) == 0.0

    def test_no_price_text(self):
        assert parse_price("Contact for price") == 0.0

    def test_price_with_html_artifacts(self):
        assert parse_price("$42.99\xa0USD") == 42.99

    def test_price_in_messy_text(self):
        assert parse_price("Sale Price: $19.99 each") == 19.99


class TestGetRandomUA:
    def test_returns_string(self):
        ua = get_random_ua()
        assert isinstance(ua, str)
        assert "Mozilla" in ua

    def test_returns_from_pool(self):
        # Should always return a valid browser UA (Chrome, Safari, or Firefox)
        for _ in range(20):
            ua = get_random_ua()
            assert any(browser in ua for browser in ("Chrome", "Safari", "Firefox"))


class TestDefaultHeaders:
    def test_has_user_agent(self):
        headers = default_headers()
        assert "User-Agent" in headers

    def test_has_accept(self):
        headers = default_headers()
        assert "Accept" in headers

    def test_has_accept_language(self):
        headers = default_headers()
        assert "Accept-Language" in headers
