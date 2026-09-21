"""
Tests for SafetyPolicy.evaluate().

This is the function that decides what the agent is allowed to do
autonomously. Its behaviour is money-critical: if it says 'autonomous'
for something it shouldn't, the agent can act without human approval.
"""

import pytest
from src.policies.safety import SafetyPolicy, ActionPolicy


@pytest.fixture
def safety():
    return SafetyPolicy()


# ─────────────────────────────────────────────────────────────
# Unknown actions
# ─────────────────────────────────────────────────────────────

def test_unknown_action_requires_human_review(safety):
    """An action not in the policy list should never be autonomous."""
    result = safety.evaluate({
        "action_name": "delete_everything",
        "brand_id": 1,
        "confidence": 0.99,
        "estimated_impact": 0,
    })
    assert result["autonomous"] is False
    assert result["requires_approval"] is True
    assert "Unknown action" in result["reason"]


# ─────────────────────────────────────────────────────────────
# Low-risk autonomous actions
# ─────────────────────────────────────────────────────────────

def test_resolve_seo_issue_requires_approval_in_recommend_only_mode(safety):
    """
    We run in recommend-only mode. resolve_seo_issue is high-confidence
    low-risk, but still requires human approval until the learning loop
    has proven itself against real affiliate revenue.
    """
    result = safety.evaluate({
        "action_name": "resolve_seo_issue",
        "brand_id": 1,
        "confidence": 0.9,
        "estimated_impact": 0,
    })
    assert result["allowed"] is True
    assert result["autonomous"] is False
    assert result["requires_approval"] is True

def test_no_action_needed_always_allowed(safety):
    """no_action_needed is a no-op; always permitted."""
    result = safety.evaluate({
        "action_name": "no_action_needed",
        "brand_id": 1,
        "confidence": 0.0,
        "estimated_impact": 0,
    })
    assert result["allowed"] is True


# ─────────────────────────────────────────────────────────────
# High-risk actions always need approval
# ─────────────────────────────────────────────────────────────

def test_pause_campaign_requires_approval_even_at_full_confidence(safety):
    """
    pause_campaign is high-risk: even with confidence=1.0 it must
    require human approval. This is the core safety guarantee.
    """
    result = safety.evaluate({
        "action_name": "pause_campaign",
        "brand_id": 1,
        "confidence": 1.0,
        "estimated_impact": 100,
    })
    assert result["autonomous"] is False
    assert result["requires_approval"] is True


def test_pause_campaign_rejects_impact_over_limit(safety):
    """max_impact=5000; going over forces human approval."""
    result = safety.evaluate({
        "action_name": "pause_campaign",
        "brand_id": 1,
        "confidence": 0.9,
        "estimated_impact": 10000,
    })
    assert result["autonomous"] is False
    assert "exceeds limit" in result["reason"]


# ─────────────────────────────────────────────────────────────
# Confidence thresholds
# ─────────────────────────────────────────────────────────────

def test_low_confidence_requires_approval(safety):
    """Below AUTONOMOUS_THRESHOLD (0.8), requires approval."""
    result = safety.evaluate({
        "action_name": "resolve_seo_issue",
        "brand_id": 1,
        "confidence": 0.5,
        "estimated_impact": 0,
    })
    assert result["autonomous"] is False


def test_reasoning_required_action_below_threshold(safety):
    """trigger_content_generation needs reasoning + confidence."""
    result = safety.evaluate({
        "action_name": "trigger_content_generation",
        "brand_id": 1,
        "confidence": 0.6,
        "estimated_impact": 0,
    })
    assert result["autonomous"] is False


# ─────────────────────────────────────────────────────────────
# Frequency cap (item 3)
# ─────────────────────────────────────────────────────────────

def test_frequency_cap_blocks_when_count_at_limit(safety):
    """If recent_count >= max_frequency_per_hour, block."""
    # resolve_seo_issue has max_frequency_per_hour=50
    result = safety.evaluate({
        "action_name": "resolve_seo_issue",
        "brand_id": 1,
        "confidence": 0.9,
        "estimated_impact": 0,
        "recent_count": 50,
    })
    assert result["autonomous"] is False
    assert "Hourly cap" in result["reason"]


def test_frequency_cap_allows_when_count_below_limit(safety):
    """
    Under the cap → frequency check passes. Autonomy is still False
    (recommend-only mode), but the *reason* should not be the cap.
    """
    result = safety.evaluate({
        "action_name": "resolve_seo_issue",
        "brand_id": 1,
        "confidence": 0.9,
        "estimated_impact": 0,
        "recent_count": 49,
    })
    assert result["allowed"] is True
    # Not blocked by frequency — reason should not mention the cap
    assert "Hourly cap" not in result["reason"]

def test_frequency_cap_skipped_when_count_none(safety):
    """
    If orchestrator couldn't fetch the count, the frequency check is
    skipped — we don't block on missing data. Autonomy is still False
    due to recommend-only mode.
    """
    result = safety.evaluate({
        "action_name": "resolve_seo_issue",
        "brand_id": 1,
        "confidence": 0.9,
        "estimated_impact": 0,
        "recent_count": None,
    })
    assert result["allowed"] is True
    assert "Hourly cap" not in result["reason"]


# ─────────────────────────────────────────────────────────────
# Tenant isolation
# ─────────────────────────────────────────────────────────────

def test_tenant_isolation_blocks_unauthorized_brand(safety):
    """
    Actions with allowed_brands set must reject brands not in the list.
    Currently no default action uses allowed_brands, so we test the
    mechanism by injecting a policy directly.
    """
    safety.policies["test_action"] = ActionPolicy(
        action_name="test_action",
        allowed_brands=[1, 2],
        risk_level="low",
    )
    result = safety.evaluate({
        "action_name": "test_action",
        "brand_id": 999,
        "confidence": 0.9,
        "estimated_impact": 0,
    })
    assert result["autonomous"] is False
    assert "not authorized" in result["reason"].lower()