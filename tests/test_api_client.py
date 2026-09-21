# tests/test_api_client.py

"""
Tests for LaravelApiClient.

These use respx to mock httpx.AsyncClient responses, since the client
switched from requests.Session to httpx.AsyncClient.

Every test asserts on the URL, method, and response shape the client
is expected to produce. If any of those change without a corresponding
update here, the test fails.
"""

import importlib
import os
import sys

import pytest
import respx
import httpx

# Add src to path so tests can import the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.api_client import LaravelApiClient


BASE_URL = "https://test.example.com"


@pytest.fixture
def client():
    """A client pointed at a fake base URL, with a known API key."""
    return LaravelApiClient(base_url=BASE_URL, api_key="test-key")


# ─────────────────────────────────────────────────────────────
# Response parsing
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_opportunities(client):
    """get_opportunities unwraps the 'opportunities' key from the response."""
    with respx.mock(base_url=BASE_URL, assert_all_called=True) as mock:
        mock.get("/agent/opportunities/1").mock(
            return_value=httpx.Response(
                200,
                json={"opportunities": [{"id": 1, "type": "seo_issue"}], "total": 1},
            )
        )
        result = await client.get_opportunities(1)
        assert len(result) == 1
        assert result[0]["type"] == "seo_issue"


@pytest.mark.asyncio
async def test_get_analytics(client):
    """get_analytics returns the full analytics payload unchanged."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/agent/analytics/1").mock(
            return_value=httpx.Response(
                200,
                json={"visitors": 1000, "conversions": 50},
            )
        )
        result = await client.get_analytics(1)
        assert result["visitors"] == 1000
        assert result["conversions"] == 50


@pytest.mark.asyncio
async def test_get_seo_recommendations(client):
    """get_seo_recommendations returns the raw payload."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/agent/seo/recommendations/1/issue-123").mock(
            return_value=httpx.Response(
                200,
                json={"recommendations": [{"priority": "high", "action": "rewrite meta title"}]},
            )
        )
        result = await client.get_seo_recommendations(1, "issue-123")
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["action"] == "rewrite meta title"


@pytest.mark.asyncio
async def test_get_seo_issues_unwraps_issues_key(client):
    """get_seo_issues returns the inner list, not the wrapper."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/agent/seo/issues/1").mock(
            return_value=httpx.Response(
                200,
                json={"issues": [{"id": 10, "type": "missing_meta"}], "score": 80},
            )
        )
        result = await client.get_seo_issues(1)
        assert isinstance(result, list)
        assert result[0]["type"] == "missing_meta"


# ─────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sends_api_key_header(client):
    """Every request includes the X-API-Key header."""
    with respx.mock(base_url=BASE_URL) as mock:
        route = mock.get("/agent/analytics/1").mock(
            return_value=httpx.Response(200, json={})
        )
        await client.get_analytics(1)

        assert route.called
        headers = route.calls.last.request.headers
        assert headers["x-api-key"] == "test-key"


# ─────────────────────────────────────────────────────────────
# Newer endpoints (item 3 + A1-A4)
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_action_count(client):
    """get_action_count returns the frequency-cap count."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/agent/actions/count/1").mock(
            return_value=httpx.Response(
                200,
                json={"success": True, "category": "seo", "count": 5},
            )
        )
        result = await client.get_action_count(1, "seo")
        assert result["count"] == 5
        assert result["category"] == "seo"


@pytest.mark.asyncio
async def test_get_action_metrics(client):
    """get_action_metrics returns metrics + attribution."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/agent/metrics/1/90").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "action_id": 90,
                    "category": "seo",
                    "metrics": {"open_seo_issues": 2, "resolved_seo_issues": 1},
                    "attribution": "agent",
                },
            )
        )
        result = await client.get_action_metrics(1, 90)
        assert result["attribution"] == "agent"
        assert result["metrics"]["open_seo_issues"] == 2


@pytest.mark.asyncio
async def test_execute_action(client):
    """execute_action posts to the right route."""
    with respx.mock(base_url=BASE_URL) as mock:
        route = mock.post("/agent/actions/42/execute").mock(
            return_value=httpx.Response(
                200,
                json={"success": True, "action_id": 42, "result": {"dispatched": "GenerateContentForActionJob"}},
            )
        )
        result = await client.execute_action(42)
        assert result["action_id"] == 42
        assert route.called


# ─────────────────────────────────────────────────────────────
# Rollback (renamed from rollback_action)
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_request_rollback(client):
    """request_rollback posts to the request-rollback route."""
    with respx.mock(base_url=BASE_URL) as mock:
        route = mock.post("/agent/actions/42/request-rollback").mock(
            return_value=httpx.Response(
                200,
                json={"success": True, "action_id": 42, "status": "rolled_back"},
            )
        )
        result = await client.request_rollback(42, "Day-1 failed")
        assert result["success"] is True
        assert route.called
        body = route.calls.last.request.content
        assert b"Day-1 failed" in body


# ─────────────────────────────────────────────────────────────
# Error handling
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_404_raises_http_status_error(client):
    """A 404 is not silently swallowed."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/agent/analytics/999").mock(
            return_value=httpx.Response(404, json={"error": "not found"})
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_analytics(999)


@pytest.mark.asyncio
async def test_get_brief_returns_404_as_dict(client):
    """get_brief catches its own 404 and returns {'success': False}."""
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/agent/brief/1").mock(
            return_value=httpx.Response(404, json={"error": "no brief"})
        )
        result = await client.get_brief(1)
        assert result["success"] is False


# ─────────────────────────────────────────────────────────────
# Entrypoint sanity
# ─────────────────────────────────────────────────────────────

def test_main_module_imports():
    """The application entry point imports cleanly as a package."""
    module = importlib.import_module('src.main')
    assert hasattr(module, 'run_cycle')