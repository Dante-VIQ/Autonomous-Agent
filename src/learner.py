# src/learner.py

import asyncio
import logging
from typing import Dict, Any
from .utils.api_client import LaravelApiClient
from .memory.experience import ExperienceMemory

logger = logging.getLogger(__name__)

class Learner:
    """Records learning outcomes for future decisions."""
    
    def __init__(self):
        self.client = LaravelApiClient()
        self.memory = ExperienceMemory()
    
    async def record(self, opportunity: Dict, decision: Dict, execution: Dict, verification: Dict, brand_id: int) -> Dict:
        """Record a complete learning cycle."""

        # Verifier returns a flat improvement_score, not a nested dict.
        improvement = verification.get("improvement_score", 0) if verification else 0
        was_successful = verification.get("was_successful", None) if verification else None

        learning = {
            "opportunity_type": opportunity.get("type", "unknown"),
            "severity": opportunity.get("severity", "medium"),
            "action_name": (decision.get("action") or {}).get("name", "unknown"),
            "confidence": decision.get("confidence", 0.0),
            "was_autonomous": execution.get("status") == "executed",
            "was_successful": bool(was_successful) if was_successful is not None else False,
            "improvement_percentage": improvement * 100,
            "duration_seconds": execution.get("duration", 0),
            "context": {
                "opportunity": opportunity,
                "decision": decision,
                "execution": execution,
                "verification": verification,
            },
            "learning_type": self._determine_learning_type(verification or {}),
        }

        result = await self.client.record_learning(brand_id, learning)

        logger.info(
            f"📝 Learning recorded for {learning['action_name']} "
            f"(status={'pending' if was_successful is None else 'verified'})"
        )

        return result
    
    def _determine_learning_type(self, verification: Dict) -> str:
        """Determine what type of learning occurred."""
        was_successful = verification.get("was_successful")
        if was_successful is None:
            return "pending_verification"
        if not was_successful:
            return "failure"

        improvement = verification.get("improvement_score", 0)
        if improvement > 0.15:
            return "significant_success"
        elif improvement > 0.05:
            return "moderate_success"
        else:
            return "marginal_success"

    async def record_rejection(self, action_id: int, reason: str, brand_id: int, notes: str = None):
        """Record a human rejection as a negative learning experience."""
        try:
            result = await self.client.record_learning(brand_id, {
                "action_name": "human_review",
                "opportunity_type": "rejection",
                "severity": "high",
                "was_autonomous": True,
                "was_successful": False,
                "confidence": 0.0,
                "human_feedback": reason,
                "context": {
                    "action_id": action_id,
                    "rejection_reason": reason,
                    "notes": notes,
                },
            })
            logger.info(f"📉 Recorded rejection for action {action_id}: {reason}")
            return result
        except Exception as e:
            logger.warning(f"Failed to record rejection: {e}")
            return {"success": False, "error": str(e)}