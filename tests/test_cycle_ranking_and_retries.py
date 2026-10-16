import json
import os
import sys

import httpx
import pytest
import respx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.orchestrator import opportunity_priority, summarize_results
from src.utils.api_client import LaravelApiClient
import src.main as main_mod

BASE = "https://test.example.com"


def test_priority_orders_by_severity_then_recurrence_then_impact():
    crit = opportunity_priority({"severity": "critical"}, {})
    high = opportunity_priority({"severity": "high"}, {})
    low_recurring = opportunity_priority({"severity": "low"}, {"recurrence_count": 5})
    assert crit > high > low_recurring
    big = opportunity_priority({"severity": "high", "estimated_impact": 9000}, {})
    assert high < big < crit  # impact helps but cannot beat a severity tier


def test_priority_tolerates_bad_values():
    assert opportunity_priority({"severity": None, "estimated_impact": "n/a"}, {"recurrence_count": None}) > 0


def test_summarize_results():
    counts = summarize_results([
        {"execution": {"status": "executed"}},
        {"execution": {"status": "requires_approval"}},
        {"execution": {"status": "timeout"}},
        {"success": False, "error": "boom"},
        {"success": True, "escalated": True},
    ])
    assert counts["executed"] == 1
    assert counts["requires_approval"] == 1
    assert counts["failed"] == 2
    assert counts["escalated"] == 1


@pytest.mark.asyncio
async def test_post_read_timeout_is_not_retried():
    c = LaravelApiClient(base_url=BASE, api_key="k")
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/agent/content/generate").mock(side_effect=httpx.ReadTimeout("slow"))
        with pytest.raises(httpx.ReadTimeout):
            await c.generate_content(1, "topic")
        assert route.call_count == 1  # no duplicate content actions


@pytest.mark.asyncio
async def test_get_read_timeout_is_retried(monkeypatch):
    async def no_sleep(_):
        return None
    monkeypatch.setattr("src.utils.api_client.asyncio.sleep", no_sleep)
    c = LaravelApiClient(base_url=BASE, api_key="k")
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/agent/analytics/1").mock(side_effect=[
            httpx.ReadTimeout("slow"), httpx.Response(200, json={"ok": 1}),
        ])
        assert (await c.get_analytics(1)) == {"ok": 1}
        assert route.call_count == 2


@pytest.mark.asyncio
async def test_action_count_sends_action_name():
    c = LaravelApiClient(base_url=BASE, api_key="k")
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/agent/actions/count/1").mock(
            return_value=httpx.Response(200, json={"count": 2}))
        await c.get_action_count(1, "strategy", action_name="pause_campaign")
        params = route.calls.last.request.url.params
        assert params["action"] == "pause_campaign"
        assert params["category"] == "strategy"


@pytest.mark.asyncio
async def test_record_cycle_run_payload():
    c = LaravelApiClient(base_url=BASE, api_key="k")
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/agent/cycles").mock(return_value=httpx.Response(201, json={}))
        await c.record_cycle_run(2, "completed", {"counts": {}}, "a", "b")
        body = json.loads(route.calls.last.request.content)
        assert body["brand_id"] == 2 and body["status"] == "completed"


@pytest.mark.asyncio
async def test_resolve_brand_ids(monkeypatch):
    monkeypatch.setattr(main_mod.Config, "BRAND_ID", 9)
    monkeypatch.setattr(main_mod.Config, "AGENT_BRANDS", "")
    assert await main_mod.resolve_brand_ids() == [9]
    monkeypatch.setattr(main_mod.Config, "AGENT_BRANDS", "1, 3,7")
    assert await main_mod.resolve_brand_ids() == [1, 3, 7]
