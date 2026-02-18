"""Tests for Reddit community integration."""

import pytest

from app.services.community import CommunityThread, fetch_community_discussions


@pytest.mark.asyncio
async def test_fetch_community_disabled(monkeypatch):
    """When community is disabled, return empty list."""
    from app.config import settings

    monkeypatch.setattr(settings, "community_enabled", False)
    result = await fetch_community_discussions("BMW oil filter")
    assert result == []


@pytest.mark.asyncio
async def test_fetch_community_cached(monkeypatch):
    """Return cached results when available."""
    cached_threads = [
        CommunityThread(
            title="Best oil filter for E46?",
            url="https://www.reddit.com/r/BMW/comments/abc123/best_oil_filter_for_e46/",
            subreddit="BMW",
            score=42,
        )
    ]

    async def mock_cached(query):
        return cached_threads

    monkeypatch.setattr("app.services.community._get_cached_community", mock_cached)

    result = await fetch_community_discussions("BMW E46 oil filter")
    assert len(result) == 1
    assert result[0].title == "Best oil filter for E46?"
    assert result[0].score == 42


@pytest.mark.asyncio
async def test_fetch_community_from_reddit(monkeypatch):
    """Mock Reddit JSON API and verify parsing."""
    import httpx

    reddit_response = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Best oil filter brand for E46 M54?",
                        "permalink": "/r/BMW/comments/xyz/best_oil_filter_brand/",
                        "score": 25,
                        "removed_by_category": None,
                    }
                },
                {
                    "data": {
                        "title": "Low quality post",
                        "permalink": "/r/BMW/comments/low/low_quality/",
                        "score": 2,
                        "removed_by_category": None,
                    }
                },
                {
                    "data": {
                        "title": "Removed post",
                        "permalink": "/r/BMW/comments/rem/removed/",
                        "score": 50,
                        "removed_by_category": "moderator",
                    }
                },
            ]
        }
    }

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return reddit_response

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: MockClient())

    # No cache
    async def no_cache(query):
        return None

    async def noop_cache(query, threads):
        pass

    monkeypatch.setattr("app.services.community._get_cached_community", no_cache)
    monkeypatch.setattr("app.services.community._cache_community", noop_cache)

    result = await fetch_community_discussions(
        "BMW E46 oil filter",
        vehicle_hint="BMW E46",
        part_description="oil filter",
    )
    # Should only include posts with score >= 5 and not removed
    assert len(result) >= 1
    assert all(t.score >= 5 for t in result)
    assert all("removed" not in t.title.lower() for t in result)


@pytest.mark.asyncio
async def test_fetch_community_rate_limited(monkeypatch):
    """Reddit rate limiting should return empty gracefully."""
    import httpx

    class MockResponse:
        status_code = 429

        def raise_for_status(self):
            raise httpx.HTTPStatusError("Rate limited", request=None, response=self)

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: MockClient())

    async def no_cache(query):
        return None

    async def noop_cache(query, threads):
        pass

    monkeypatch.setattr("app.services.community._get_cached_community", no_cache)
    monkeypatch.setattr("app.services.community._cache_community", noop_cache)

    result = await fetch_community_discussions("oil filter")
    assert result == []
