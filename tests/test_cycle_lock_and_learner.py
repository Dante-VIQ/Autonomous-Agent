import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.lock import cycle_lock
from src.learner import Learner


def test_cycle_lock_blocks_second_holder(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_LOCK_DIR", str(tmp_path))
    with cycle_lock(1) as first:
        assert first is True
        with cycle_lock(1) as second:
            assert second is False
        with cycle_lock(2) as other_brand:
            assert other_brand is True
    with cycle_lock(1) as again:
        assert again is True


class _FakeClient:
    def __init__(self):
        self.sent = None

    async def record_learning(self, brand_id, data):
        self.sent = data
        return {}


class _FakeMemory:
    pass


def _learner():
    l = Learner.__new__(Learner)
    l.client = _FakeClient()
    l.memory = _FakeMemory()
    return l


@pytest.mark.asyncio
async def test_unknown_outcome_is_not_recorded_as_failure():
    l = _learner()
    await l.record(
        {"type": "seo_issue"},
        {"action": {"name": "run_site_scan"}, "confidence": 0.9},
        {"status": "executed", "duration": 1.6},
        {"was_successful": None, "improvement_score": 0},
        1,
    )
    assert l.client.sent["was_successful"] is None
    assert l.client.sent["duration_seconds"] == 2
    assert isinstance(l.client.sent["duration_seconds"], int)


@pytest.mark.asyncio
async def test_known_outcome_preserved():
    l = _learner()
    await l.record({}, {"action": {"name": "x"}}, {"status": "executed"},
                   {"was_successful": True, "improvement_score": 0.1}, 1)
    assert l.client.sent["was_successful"] is True
