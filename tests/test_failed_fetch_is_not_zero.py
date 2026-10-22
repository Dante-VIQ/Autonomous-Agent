"""A failed read must never be reported as "nothing found". Reproduces the 401 run: the server rejected the key and the
agent logged "No verifications due / Found 0 opportunities / Cycle completed"."""
import asyncio
import os
import sys

import httpx
import pytest
import respx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("LARAVEL_API_KEY", "k")
os.environ.setdefault("GEMINI_API_KEY", "g")

from src.orchestrator import Orchestrator, MonitorError
from src.utils.api_client import LaravelApiClient

BASE = "http://laravel.test/api"


@pytest.fixture
def orch(monkeypatch):
    monkeypatch.setattr("src.config.Config.LARAVEL_API_URL", BASE, raising=False)
    monkeypatch.setattr("src.config.Config.LARAVEL_API_KEY", "wrong-key", raising=False)
    o = Orchestrator(1)
    o.client = LaravelApiClient(base_url=BASE, api_key="wrong-key")
    o.verifier.client = o.client
    return o


@respx.mock
def test_rejected_key_stops_the_cycle_with_a_clear_reason(orch):
    respx.route().mock(return_value=httpx.Response(401, json={"error": "Unauthorized"}))
    result = asyncio.run(orch.run_cycle())
    assert result["status"] == "failed"
    assert "API key" in result["error"] and "401" in result["error"]
    assert "LARAVEL_API_KEY" in result["error"]
    # it stopped at the first call instead of making a dozen more doomed ones
    assert len([c for c in respx.calls if "/data-status/" in str(c.request.url)]) == 1
    assert not any("/opportunities/" in str(c.request.url) for c in respx.calls)


@respx.mock
def test_failed_discovery_is_an_error_not_zero_opportunities(orch):
    respx.get(f"{BASE}/agent/data-status/1").mock(return_value=httpx.Response(200, json={"all_fresh": True}))
    respx.get(f"{BASE}/agent/brief/1").mock(return_value=httpx.Response(404, json={"success": False}))
    respx.get(f"{BASE}/agent/tours/1").mock(return_value=httpx.Response(200, json={"success": True, "tours": []}))
    respx.get(f"{BASE}/agent/actions/outcomes/1").mock(return_value=httpx.Response(200, json={"outcomes": []}))
    respx.get(f"{BASE}/agent/verification/due/1").mock(return_value=httpx.Response(200, json={"hour_1": [], "day_1": []}))
    respx.get(f"{BASE}/agent/opportunities/1").mock(return_value=httpx.Response(500, json={"message": "boom"}))
    respx.post(f"{BASE}/agent/cycles").mock(return_value=httpx.Response(200, json={}))
    result = asyncio.run(orch.run_cycle())
    assert result["status"] == "failed"          # not "idle"
    assert "discovery failed" in result["error"]


@respx.mock
def test_genuinely_empty_discovery_is_still_idle(orch):
    respx.get(f"{BASE}/agent/data-status/1").mock(return_value=httpx.Response(200, json={"all_fresh": True}))
    respx.get(f"{BASE}/agent/brief/1").mock(return_value=httpx.Response(404, json={"success": False}))
    respx.get(f"{BASE}/agent/tours/1").mock(return_value=httpx.Response(200, json={"success": True, "tours": []}))
    respx.get(f"{BASE}/agent/actions/outcomes/1").mock(return_value=httpx.Response(200, json={"outcomes": []}))
    respx.get(f"{BASE}/agent/verification/due/1").mock(return_value=httpx.Response(200, json={"hour_1": [], "day_1": []}))
    respx.get(f"{BASE}/agent/opportunities/1").mock(return_value=httpx.Response(200, json={"opportunities": [], "total": 0}))
    respx.post(f"{BASE}/agent/cycles").mock(return_value=httpx.Response(200, json={}))
    assert asyncio.run(orch.run_cycle())["status"] == "idle"


@respx.mock
def test_verification_fetch_failure_is_reported_as_unknown(orch):
    respx.get(f"{BASE}/agent/verification/due/1").mock(return_value=httpx.Response(500, json={}))
    out = asyncio.run(orch.verifier.run_due_verifications(1))
    assert "error" in out and out["hour_1"] == 0
