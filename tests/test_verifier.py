"""
Tests for Verifier.decide_success() and _score_improvement().

These are the functions that decide whether an action "worked". If they
are wrong, the calibration data is wrong, and the agent's confidence
model becomes fiction.
"""

import pytest
from src.verifier import Verifier


@pytest.fixture
def verifier():
    # api_client=None is fine; decide_success, _score_improvement and
    # _compute_deltas don't touch the network
    return Verifier(api_client=None)


# ─────────────────────────────────────────────────────────────
# decide_success — the core honesty function
# ─────────────────────────────────────────────────────────────

def test_decide_success_agent_improvement_above_threshold(verifier):
    """Agent's action, 10% improvement, above 5% threshold → True."""
    assert verifier.decide_success(0.10, attribution="agent") is True


def test_decide_success_agent_improvement_below_threshold(verifier):
    """Agent's action, 2% improvement, below 5% threshold → False."""
    assert verifier.decide_success(0.02, attribution="agent") is False


def test_decide_success_agent_negative_improvement(verifier):
    """Agent's action made things worse → False."""
    assert verifier.decide_success(-0.20, attribution="agent") is False


def test_decide_success_human_attribution_is_none(verifier):
    """
    Human fixed it → inconclusive, not True or False.
    This is critical: we must NOT credit the agent for human work.
    """
    assert verifier.decide_success(0.50, attribution="human") is None


def test_decide_success_mixed_attribution_is_none(verifier):
    """Mixed human + agent → also inconclusive."""
    assert verifier.decide_success(0.50, attribution="mixed") is None


def test_decide_success_unknown_attribution_proceeds(verifier):
    """
    If we can't determine attribution, fall through to numeric judgement.
    """
    assert verifier.decide_success(0.10, attribution="unknown") is True
    assert verifier.decide_success(0.01, attribution="unknown") is False


def test_decide_success_at_exact_threshold(verifier):
    """Exactly at 5% → should be True (>= semantics)."""
    assert verifier.decide_success(0.05, attribution="agent") is True


# ─────────────────────────────────────────────────────────────
# _score_improvement — the numeric averaging
# ─────────────────────────────────────────────────────────────

def test_score_improvement_empty_deltas(verifier):
    """No deltas → 0.0, not a crash."""
    assert verifier._score_improvement({}) == 0.0


def test_score_improvement_single_positive(verifier):
    """One delta, +20% → 0.20."""
    deltas = {"clicks": {"pct": 0.20, "before": 100, "after": 120, "abs": 20}}
    assert verifier._score_improvement(deltas) == pytest.approx(0.20)


def test_score_improvement_mixed_signs(verifier):
    """+20% and -10% → average 0.05."""
    deltas = {
        "clicks":      {"pct": 0.20},
        "conversions": {"pct": -0.10},
    }
    assert verifier._score_improvement(deltas) == pytest.approx(0.05)


def test_score_improvement_caps_extremes(verifier):
    """Deltas are clamped to [-1, 1] before averaging."""
    deltas = {
        "clicks": {"pct": 5.0},
        "views":  {"pct": -3.0},
    }
    assert verifier._score_improvement(deltas) == pytest.approx(0.0)


def test_score_improvement_ignores_none_pct(verifier):
    """pct=None (e.g. before was 0) is ignored, not crash."""
    deltas = {
        "clicks": {"pct": 0.10},
        "views":  {"pct": None, "before": 0, "after": 5, "abs": 5},
    }
    assert verifier._score_improvement(deltas) == pytest.approx(0.10)


def test_score_improvement_all_none_pct(verifier):
    """Everything None → 0.0, not a crash."""
    deltas = {
        "clicks": {"pct": None},
        "views":  {"pct": None},
    }
    assert verifier._score_improvement(deltas) == 0.0


# ─────────────────────────────────────────────────────────────
# _compute_deltas — the arithmetic
# ─────────────────────────────────────────────────────────────

def test_compute_deltas_simple_increase(verifier):
    """100 → 120 = +20%."""
    deltas = verifier._compute_deltas({"clicks": 100}, {"clicks": 120})
    assert deltas["clicks"]["pct"] == pytest.approx(0.20)
    assert deltas["clicks"]["abs"] == 20


def test_compute_deltas_zero_before(verifier):
    """0 → 10 = pct=None, abs=10."""
    deltas = verifier._compute_deltas({"clicks": 0}, {"clicks": 10})
    assert deltas["clicks"]["pct"] is None
    assert deltas["clicks"]["abs"] == 10


def test_compute_deltas_both_zero_skipped(verifier):
    """0 → 0 = not a meaningful delta, skip it."""
    deltas = verifier._compute_deltas({"clicks": 0}, {"clicks": 0})
    assert "clicks" not in deltas


def test_compute_deltas_skips_stated_confidence(verifier):
    """stated_confidence isn't a metric; it shouldn't appear in deltas."""
    deltas = verifier._compute_deltas(
        {"clicks": 100, "stated_confidence": 0.85},
        {"clicks": 120},
    )
    assert "stated_confidence" not in deltas
    assert "clicks" in deltas