import os
import sys

import httpx
import pytest
import respx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.executor import Executor
from src.utils.api_client import LaravelApiClient

BASE = "https://test.example.com"


@pytest.fixture
def executor():
    ex = Executor()
    ex.client = LaravelApiClient(base_url=BASE, api_key="k")
    return ex


@pytest.mark.asyncio
async def test_adjust_campaign_hits_adjust_endpoint_not_pause(executor):
    with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        adjust = mock.post("/agent/campaigns/adjust").mock(
            return_value=httpx.Response(200, json={"success": True, "action_id": 7}))
        pause = mock.post("/agent/campaigns/pause").mock(return_value=httpx.Response(200, json={}))
        res = await executor.execute(
            {"action": {"name": "adjust_campaign", "payload": {"campaign_id": 3, "daily_budget": 12.5, "reason": "x"}}}, 1)
    assert res["status"] == "executed" and res["action_id"] == 7
    assert adjust.called and not pause.called
    assert b'"dailyBudget":12.5' in adjust.calls[0].request.content.replace(b" ", b"")


@pytest.mark.asyncio
async def test_adjust_without_budget_fails_instead_of_pausing(executor):
    with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        pause = mock.post("/agent/campaigns/pause").mock(return_value=httpx.Response(200, json={}))
        res = await executor.execute({"action": {"name": "adjust_campaign", "payload": {"campaign_id": 3}}}, 1)
    assert res["status"] == "failed"
    assert not pause.called


@pytest.mark.asyncio
async def test_pause_campaign_hits_pause_endpoint(executor):
    with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        pause = mock.post("/agent/campaigns/pause").mock(
            return_value=httpx.Response(200, json={"success": True, "action_id": 9}))
        res = await executor.execute({"action": {"name": "pause_campaign", "payload": {"campaign_id": 3}}}, 1)
    assert res["action_id"] == 9 and pause.called
