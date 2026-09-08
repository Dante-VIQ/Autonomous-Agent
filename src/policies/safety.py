# src/policies/safety.py

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from ..config import Config

logger = logging.getLogger(__name__)

@dataclass
class ActionPolicy:
    action_name: str
    requires_approval: bool = False
    max_impact: Optional[float] = None
    max_frequency_per_hour: Optional[int] = None
    allowed_brands: Optional[List[int]] = None
    requires_reasoning: bool = False
    reversible: bool = False
    risk_level: str = "low"

class SafetyPolicy:
    """Deterministic safety gate that overrides LLM decisions."""
    
    def __init__(self):
        self.policies = {
            "resolve_seo_issue": ActionPolicy(
                action_name="resolve_seo_issue",
                requires_approval=False,
                max_frequency_per_hour=50,
                requires_reasoning=False,
                reversible=True,
                risk_level="low"
            ),
            "run_site_scan": ActionPolicy(
                action_name="run_site_scan",
                requires_approval=False,
                max_frequency_per_hour=10,
                reversible=True,
                risk_level="low"
            ),
            "trigger_content_generation": ActionPolicy(
                action_name="trigger_content_generation",
                requires_approval=False,
                max_frequency_per_hour=5,
                requires_reasoning=True,
                reversible=False,
                risk_level="medium"
            ),
            "notify_lead_response": ActionPolicy(
                action_name="notify_lead_response",
                requires_approval=False,
                max_frequency_per_hour=20,
                requires_reasoning=True,
                reversible=False,
                risk_level="medium"
            ),
            "pause_campaign": ActionPolicy(
                action_name="pause_campaign",
                requires_approval=True,
                max_frequency_per_hour=3,
                requires_reasoning=True,
                reversible=True,
                risk_level="high",
                max_impact=5000
            ),
            "no_action_needed": ActionPolicy(
                action_name="no_action_needed",
                requires_approval=False,
                reversible=True,
                risk_level="low"
            ),
                "create_blog_post": ActionPolicy(
        action_name="create_blog_post",
        requires_approval=False,
        requires_reasoning=True,
        reversible=False,
        risk_level="medium"
    ),
    "generate_content": ActionPolicy(
        action_name="generate_content",
        requires_approval=False,
        requires_reasoning=True,
        reversible=False,
        risk_level="medium"
    ),
        }
    
    def evaluate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a request against the safety policy."""
        action_name = request.get("action_name", "unknown")
        brand_id = request.get("brand_id")
        estimated_impact = request.get("estimated_impact")
        confidence = request.get("confidence", 0.0)
        
        policy = self.policies.get(action_name)
        
        if not policy:
            logger.warning(f"Unknown action: {action_name}, routing to human review")
            return {
                "allowed": False,
                "autonomous": False,
                "requires_approval": True,
                "reason": f"Unknown action '{action_name}'. Routing to human review.",
                "risk_level": "critical"
            }
        
        # Tenant isolation
        if policy.allowed_brands and brand_id not in policy.allowed_brands:
            return {
                "allowed": False,
                "autonomous": False,
                "requires_approval": True,
                "reason": f"Brand {brand_id} is not authorized for this action.",
                "risk_level": policy.risk_level
            }
        
        # Impact check
        if estimated_impact and policy.max_impact and estimated_impact > policy.max_impact:
            return {
                "allowed": False,
                "autonomous": False,
                "requires_approval": True,
                "reason": f"Estimated impact ${estimated_impact} exceeds limit ${policy.max_impact}.",
                "risk_level": policy.risk_level
            }
        
        # Confidence check for actions that require reasoning
        if policy.requires_reasoning and confidence < Config.AUTONOMOUS_THRESHOLD:
            return {
                "allowed": False,
                "autonomous": False,
                "requires_approval": True,
                "reason": f"Confidence {confidence:.2f} below threshold {Config.AUTONOMOUS_THRESHOLD}.",
                "risk_level": policy.risk_level
            }
        
        # Determine if autonomous execution is allowed
        is_autonomous = (
            policy.requires_approval is False and
            confidence >= Config.AUTONOMOUS_THRESHOLD and
            policy.risk_level != "critical"
        )
        
        # High risk actions always require approval
        if policy.risk_level in ["high", "critical"]:
            is_autonomous = False
        
        return {
            "allowed": True,
            "autonomous": is_autonomous,
            "requires_approval": not is_autonomous,
            "reason": f"Action '{action_name}' is {'approved for autonomous execution' if is_autonomous else 'pending human approval'}.",
            "risk_level": policy.risk_level
        }