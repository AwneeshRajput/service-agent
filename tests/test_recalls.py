import httpx
import pytest

from app.tools.recalls import MAX_RESULTS, check_recalls


@pytest.mark.asyncio
async def test_real_car_returns_recalls():
    result = await check_recalls("honda", "civic", 2019)

    assert result["error"] is None
    assert result["total"] >= 1
    assert 1 <= len(result["recalls"]) <= MAX_RESULTS
    assert result["recalls"][0]["campaign_number"]


@pytest.mark.asyncio
async def test_timeout_is_reported_not_raised(monkeypatch):
    async def slow(*args, **kwargs):
        raise httpx.ConnectTimeout("too slow")

    monkeypatch.setattr(httpx.AsyncClient, "get", slow)

    result = await check_recalls("honda", "civic", 2019)

    assert result["recalls"] == []
    assert result["error"] is not None
