"""Tests for VIN decoder service."""

import pytest

from app.services.vin_decoder import decode_vin, validate_vin


class TestValidateVin:
    def test_valid_vin(self):
        assert validate_vin("WBADT43483G024855") is None

    def test_too_short(self):
        assert validate_vin("WBADT434") is not None

    def test_too_long(self):
        assert validate_vin("WBADT43483G0248551") is not None

    def test_empty(self):
        assert validate_vin("") is not None

    def test_invalid_chars_i(self):
        assert validate_vin("WBADT43483I024855") is not None

    def test_invalid_chars_o(self):
        assert validate_vin("WBADT43483O024855") is not None

    def test_invalid_chars_q(self):
        assert validate_vin("WBADT43483Q024855") is not None

    def test_lowercase_valid(self):
        # validate_vin uses re.IGNORECASE so lowercase is fine
        assert validate_vin("wbadt43483g024855") is None


@pytest.mark.asyncio
async def test_decode_vin_invalid():
    """Invalid VIN should return error without calling API."""
    result = await decode_vin("SHORT")
    assert result.error is not None
    assert "17 characters" in result.error


@pytest.mark.asyncio
async def test_decode_vin_success(monkeypatch):
    """Mock NHTSA API to test successful decode."""
    import httpx

    nhtsa_response = {
        "Results": [
            {
                "ErrorCode": "0",
                "ModelYear": "2003",
                "Make": "BMW",
                "Model": "5 Series",
                "Trim": "530i",
                "DisplacementL": "3.0",
                "EngineModel": "M54",
                "DriveType": "Rear-Wheel Drive",
                "BodyClass": "Sedan/Saloon",
            }
        ]
    }

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return nhtsa_response

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: MockClient())

    # Also mock Redis cache (return None = not cached)
    monkeypatch.setattr(
        "app.services.vin_decoder._get_cached_vin",
        lambda vin: _async_none(),
    )
    monkeypatch.setattr(
        "app.services.vin_decoder._cache_vin",
        lambda vin, result: _async_none(),
    )

    result = await decode_vin("WBADT43483G024855")
    assert result.error is None
    assert result.year == 2003
    assert result.make == "BMW"
    assert result.model == "5 Series"
    assert result.trim == "530i"
    assert result.engine_displacement_l == 3.0
    assert result.engine_code == "M54"
    assert result.drive_type == "Rear-Wheel Drive"


@pytest.mark.asyncio
async def test_decode_vin_api_error(monkeypatch):
    """API error should return VINDecodeResult with error."""
    import httpx

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: MockClient())
    monkeypatch.setattr(
        "app.services.vin_decoder._get_cached_vin",
        lambda vin: _async_none(),
    )

    result = await decode_vin("WBADT43483G024855")
    assert result.error is not None
    assert "NHTSA" in result.error


async def _async_none():
    return None
